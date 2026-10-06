"""Keep dated daily issues; a catalogue is an internal source cache, not a daily issue."""
import argparse
import datetime as dt
import json
import time
from pathlib import Path
from fetch_history import BEIJING, atomic_json, build_issue, valid_date, validate_events


def window_dates(today, days=7):
    day = valid_date(today)
    if not 1 <= days <= 31:
        raise ValueError('Invalid retention days')
    return [(day - dt.timedelta(days=offset)).isoformat() for offset in reversed(range(days))]


def validate_issue(issue, day):
    if issue.get('schemaVersion') != 2 or issue.get('date') != day:
        raise ValueError('Archive file/date mismatch')
    validate_events(issue.get('events'))
    if any(event['date'][5:] != day[5:] or event['date'] > day for event in issue['events']):
        raise ValueError('Archive contains another month/day')
    if issue.get('status') not in ('ready', 'empty', 'unavailable'):
        raise ValueError('Invalid archive status')
    if bool(issue['events']) != (issue['status'] == 'ready'):
        raise ValueError('Archive status conflicts with events')
    return issue


def finalize_window(root, today, days=7):
    dates = window_dates(today, days)
    catalog = json.loads((root / 'catalog.json').read_text(encoding='utf-8-sig'))
    issues = []
    for day in dates:
        path = root / 'archives' / f'{day}.json'
        issue = json.loads(path.read_text(encoding='utf-8-sig')) if path.exists() else {
            **build_issue([], day), 'status': 'unavailable'}
        issues.append(validate_issue(issue, day))
    # Validate every retained file before writing or removing anything.
    archive_dir = (root / 'archives').resolve()
    archive_dir.mkdir(parents=True, exist_ok=True)
    for issue in issues:
        path = archive_dir / f'{issue["date"]}.json'
        if not path.exists(): atomic_json(path, issue)
    for path in archive_dir.glob('*.json'):
        if path.resolve().parent != archive_dir or path.is_symlink():
            raise ValueError('Unsafe archive path')
        try: valid_date(path.stem)
        except ValueError: continue
        if path.stem not in dates: path.unlink()
    index = {'schemaVersion': 1, 'today': today,
        'retentionDays': days, 'dates': dates, 'updatedAt': dt.datetime.now(BEIJING).date().isoformat(),
        'lastRun': catalog.get('lastRun')}
    diagnostic_path = root / 'collection_diagnostics' / f'{today}.json'
    if diagnostic_path.exists():
        diagnostic = json.loads(diagnostic_path.read_text(encoding='utf-8-sig'))
        if (diagnostic.get('date') == today
                and diagnostic.get('outcome') in ('ready', 'empty', 'failed', 'validation_failed', 'review_rejected')
                and isinstance(diagnostic.get('completedAt'), str)):
            index['lastAttempt'] = {key: diagnostic[key] for key in ('date', 'outcome', 'completedAt')}
    atomic_json(root / 'archive_index.json', index)
    atomic_json(root / 'issue.json', issues[-1])
    atomic_json(root / 'today_news.json', [{**event, 'year': int(event['date'][:4]),
        'subtitle': f"{event['date'][:4]}年 {event['location']}"} for event in issues[-1]['events']])


def run(root, today, days=7, backfill_budget=2, prepare_budget=0):
    from collect_history import collect
    from preparation import restore_day, checked_issue, prepare_upcoming, calendar_coverage
    if not 0 <= backfill_budget <= 6:
        raise ValueError('Backfill budget must be between 0 and 6')
    if not 0 <= prepare_budget <= 7:
        raise ValueError('Preparation budget must be between 0 and 7')
    deadline = time.monotonic() + 35 * 60
    failures = []
    dates = window_dates(today, days)
    state_path = root / 'window_status.json'
    previous = json.loads(state_path.read_text(encoding='utf-8-sig')) if state_path.exists() else {}
    retries = {day: value for day, value in previous.get('historicalRetries', {}).items() if day in dates}
    if previous.get('coveragePolicyVersion') != 2:
        retries = {}  # One-time reset for the stronger retrieval policy.
    restored = [day for day in dates if restore_day(root, day, today)]
    attempted = []
    coverage = None
    for day in reversed(dates):
        if day != today:
            if checked_issue(root / 'archives' / f'{day}.json', day, today):
                continue
            retry = retries.get(day, {'count': 0})
            if retry['count'] >= 2 or retry.get('lastAttemptDate') == today:
                continue
            if len(attempted) >= 1 + backfill_budget or time.monotonic() >= deadline:
                break  # Today is always attempted before the bounded historical work.
            retries[day] = {'count': retry['count'] + 1, 'lastAttemptDate': today}
        attempted.append(day)
        try:
            collect(root, day)
        except Exception as error:
            if not restore_day(root, day, today):
                failures.append(day)
            print(f'Collection failed for {day}: {type(error).__name__}; retaining previous issue')
        if day == today:
            coverage = prepare_upcoming(root, today, prepare_budget, deadline=deadline)
    finalize_window(root, today, days)
    if coverage is not None:
        coverage.update(calendar_coverage(root, today))
        atomic_json(root / 'coverage_status.json', coverage)
    today_diagnostic = root / 'collection_diagnostics' / f'{today}.json'
    today_attempt = (json.loads(today_diagnostic.read_text(encoding='utf-8-sig'))
                     if today_diagnostic.exists() else None)
    minimum_met = bool(checked_issue(root / 'archives' / f'{today}.json', today, today))
    if not minimum_met and today not in failures:
        failures.insert(0, today)
    atomic_json(root / 'window_status.json', {'date': today, 'failedDates': failures,
        'coveragePolicyVersion': 2, 'restoredDates': restored, 'todayMinimumMet': minimum_met,
        'preparedReadyDates': (coverage or {}).get('readyDates', []),
        'preparedMissingDates': (coverage or {}).get('missingDates', []),
        'attemptedDates': attempted, 'historicalRetries': retries,
        'todayAttempt': today_attempt})
    return failures


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--days', type=int, default=7)
    parser.add_argument('--backfill-budget', type=int, default=2,
                        help='Maximum historical dates to attempt this run (0-6; default 2)')
    parser.add_argument('--finalize-only', action='store_true')
    parser.add_argument('--prepare-budget', type=int, default=2,
                        help='Maximum missing upcoming dates to prepare this run (0-7; default 2)')
    args = parser.parse_args()
    root = Path(__file__).resolve().parent
    today = dt.datetime.now(BEIJING).date().isoformat()
    if args.finalize_only: finalize_window(root, today, args.days)
    else: run(root, today, args.days, args.backfill_budget, args.prepare_budget)
