"""Prepare a rolling week of verified history without publishing future issues."""
import datetime as dt
import calendar
import json
import time
from pathlib import Path

from fetch_history import BEIJING, atomic_json, build_issue, valid_date


def read_json(path, fallback):
    try:
        return json.loads(path.read_text(encoding='utf-8-sig'))
    except (OSError, ValueError):
        return fallback


def checked_issue(path, day, today):
    from archive_window import validate_issue
    from collect_history import verified_for_date
    try:
        raw = read_json(path, {})
        if not isinstance(raw, dict):
            return None
        issue = validate_issue(raw, day)
        events = verified_for_date(issue['events'], day, today)
        if issue['status'] == 'ready' and len(events) == len(issue['events']):
            return issue
    except (ValueError, TypeError, KeyError):
        pass
    return None


def available_events(root, day, today):
    from collect_history import verified_for_date
    draft = checked_issue(root / 'prepared' / f'{day}.json', day, today)
    if draft:
        return draft['events']
    return verified_for_date(read_json(root / 'catalog.json', {}).get('events', []), day, today)


def restore_day(root, day, today):
    from collect_history import merge_events, publish_verified
    root = Path(root)
    if valid_date(day) > valid_date(today):
        raise ValueError('Cannot publish a future prepared issue')
    if checked_issue(root / 'archives' / f'{day}.json', day, today):
        return True
    events = available_events(root, day, today)
    if not events:
        return False
    catalog = read_json(root / 'catalog.json', {})
    if catalog.get('schemaVersion') != 2:
        raise ValueError('Unsupported catalog version')
    catalog['events'] = merge_events(catalog['events'], events, replace_unverified=True)
    atomic_json(root / 'catalog.json', catalog)
    publish_verified(root, day, today)
    return True


def calendar_coverage(root, today):
    from collect_history import verified_for_date
    catalog = read_json(Path(root) / 'catalog.json', {}).get('events', [])
    calendar_year = valid_date(today).year + 1
    while not calendar.isleap(calendar_year):
        calendar_year += 1
    dates = [(dt.date(calendar_year, 1, 1) + dt.timedelta(days=n)).isoformat() for n in range(366)]
    covered = [day[5:] for day in dates if verified_for_date(catalog, day, today)]
    return {'calendarCoveredDays': len(covered), 'calendarTotalDays': 366,
            'coveredMonthDays': covered, 'annualCoverageComplete': len(covered) == 366}


def prepare_upcoming(root, today, budget=2, *, deadline=None):
    from collect_history import collect
    root = Path(root)
    start = valid_date(today)
    if not 0 <= budget <= 7:
        raise ValueError('Preparation budget must be between 0 and 7')
    dates = [(start + dt.timedelta(days=offset)).isoformat() for offset in range(1, 8)]
    state = read_json(root / 'preparation_state.json', {})
    retries = {day: value for day, value in state.get('attempts', {}).items() if day in dates}
    attempted, failed, ready = [], [], []
    for day in dates:
        events = available_events(root, day, today)
        retry = retries.get(day, {})
        count = retry.get('count', 0) if retry.get('attemptDate') == today else 0
        if not events and len(attempted) < budget and count < 3 and (deadline is None or time.monotonic() < deadline):
            attempted.append(day)
            retries[day] = {'attemptDate': today, 'count': count + 1}
            try:
                collect(root, day, prepare=True, reference_date=today)
            except Exception as error:
                failed.append(day)
                print(f'Preparation failed for {day}: {type(error).__name__}')
            events = available_events(root, day, today)
        if events:
            if not checked_issue(root / 'prepared' / f'{day}.json', day, today):
                atomic_json(root / 'prepared' / f'{day}.json', build_issue(events, day))
            ready.append(day)
    prepared = (root / 'prepared').resolve()
    prepared.mkdir(parents=True, exist_ok=True)
    retained = {(start + dt.timedelta(days=offset)).isoformat() for offset in range(-6, 8)}
    for path in prepared.glob('*.json'):
        if path.is_symlink() or path.resolve().parent != prepared:
            raise ValueError('Unsafe prepared path')
        try:
            valid_date(path.stem)
        except ValueError:
            continue
        if path.stem not in retained:
            path.unlink()
    result = {'schemaVersion': 1, 'date': today,
              'updatedAt': dt.datetime.now(BEIJING).isoformat(timespec='seconds'),
              'upcomingDates': dates, 'readyDates': ready,
              'missingDates': [day for day in dates if day not in ready],
              'attemptedDates': attempted, 'failedDates': failed,
              **calendar_coverage(root, today)}
    atomic_json(root / 'preparation_state.json', {'date': today, 'attempts': retries})
    atomic_json(root / 'coverage_status.json', result)
    return result
