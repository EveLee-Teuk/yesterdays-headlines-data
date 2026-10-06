"""Keep dated daily issues; a catalogue is an internal source cache, not a daily issue."""
import argparse
import datetime as dt
import json
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


def run(root, today, days=7, backfill_budget=2):
    from collect_history import collect
    if not 0 <= backfill_budget <= 6:
        raise ValueError('Backfill budget must be between 0 and 6')
    failures = []
    dates = window_dates(today, days)
    state_path = root / 'window_status.json'
    previous = json.loads(state_path.read_text(encoding='utf-8-sig')) if state_path.exists() else {}
    retries = {day: value for day, value in previous.get('historicalRetries', {}).items() if day in dates}
    attempted = []
    for day in reversed(dates):
        path = root / 'archives' / f'{day}.json'
        if day != today:
            if path.exists():
                issue = validate_issue(json.loads(path.read_text(encoding='utf-8-sig')), day)
                if issue['status'] == 'ready': continue
            retry = retries.get(day, {'count': 0})
            if retry['count'] >= 2 or retry.get('lastAttemptDate') == today:
                continue
            if len(attempted) >= 1 + backfill_budget:
                break  # Today is always attempted before the bounded historical work.
            retries[day] = {'count': retry['count'] + 1, 'lastAttemptDate': today}
        attempted.append(day)
        try:
            collect(root, day)
        except Exception as error:
            failures.append(day)
            print(f'Collection failed for {day}: {type(error).__name__}; retaining previous issue')
    finalize_window(root, today, days)
    today_diagnostic = root / 'collection_diagnostics' / f'{today}.json'
    today_attempt = (json.loads(today_diagnostic.read_text(encoding='utf-8-sig'))
                     if today_diagnostic.exists() else None)
    atomic_json(root / 'window_status.json', {'date': today, 'failedDates': failures,
        'attemptedDates': attempted, 'historicalRetries': retries,
        'todayAttempt': today_attempt})
    return failures


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--days', type=int, default=7)
    parser.add_argument('--backfill-budget', type=int, default=2,
                        help='Maximum historical dates to attempt this run (0-6; default 2)')
    parser.add_argument('--finalize-only', action='store_true')
    args = parser.parse_args()
    root = Path(__file__).resolve().parent
    today = dt.datetime.now(BEIJING).date().isoformat()
    if args.finalize_only: finalize_window(root, today, args.days)
    else: run(root, today, args.days, args.backfill_budget)
