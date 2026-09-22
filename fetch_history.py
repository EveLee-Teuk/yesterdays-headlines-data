"""Publish anniversaries from an editorially reviewed catalog. Never invent events."""
import argparse
import datetime as dt
import json
import os
from pathlib import Path
import re
import tempfile
from urllib.parse import urlparse

BEIJING = dt.timezone(dt.timedelta(hours=8))


def valid_date(value):
    if not isinstance(value, str) or not re.fullmatch(r'\d{4}-\d{2}-\d{2}', value):
        raise ValueError(f'Invalid ISO date: {value!r}')
    return dt.date.fromisoformat(value)


def validate_events(events):
    if not isinstance(events, list):
        raise ValueError('events must be an array')
    seen = set()
    for event in events:
        if not isinstance(event, dict):
            raise ValueError('Each event must be an object')
        for field in ('id', 'title', 'category', 'location', 'summary'):
            if not isinstance(event.get(field), str) or not event[field].strip():
                raise ValueError(f'Missing {field}')
        if not re.fullmatch(r'[a-z0-9-]+', event['id']) or event['id'] in seen:
            raise ValueError('Invalid or duplicate ID')
        seen.add(event['id'])
        event_date = valid_date(event.get('date'))
        if valid_date(event.get('reviewedAt')) < event_date:
            raise ValueError('Review predates event')
        if event['category'] not in ('科技', '民生', '社会'):
            raise ValueError('Invalid category')
        sources = event.get('sources')
        if not isinstance(sources, list) or not sources:
            raise ValueError('A reviewed source is required')
        for source in sources:
            if not isinstance(source, dict) or not isinstance(source.get('name'), str) or not source['name'].strip():
                raise ValueError('Source name is required')
            url = urlparse(source.get('url', ''))
            if url.scheme != 'https' or not url.hostname or url.username or url.password:
                raise ValueError('Source must use HTTPS')
            if source.get('date') != event['date']:
                raise ValueError('Source date conflicts with event date')
    return events


def build_issue(events, issue_date):
    day = valid_date(issue_date)
    validate_events(events)
    selected = sorted((event for event in events if event['date'][5:] == issue_date[5:]
                       and valid_date(event['date']) <= day), key=lambda event: (event['date'], event['id']))
    return {'schemaVersion': 2, 'date': issue_date, 'timezone': 'Asia/Shanghai',
            'status': 'ready' if selected else 'empty', 'events': selected}


def atomic_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(dir=path.parent, suffix='.tmp')
    try:
        with os.fdopen(descriptor, 'w', encoding='utf-8') as stream:
            json.dump(value, stream, ensure_ascii=False, indent=2)
            stream.write('\n')
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def publish(root, issue_date):
    catalog = json.loads((root / 'catalog.json').read_text(encoding='utf-8-sig'))
    if not isinstance(catalog, dict) or catalog.get('schemaVersion') != 2:
        raise ValueError('Unsupported catalog version')
    valid_date(catalog.get('updatedAt'))
    issue = build_issue(catalog.get('events'), issue_date)
    # Validate all inputs before touching outputs. CI commits outputs together.
    legacy = [{**event, 'year': int(event['date'][:4]),
               'subtitle': f"{event['date'][:4]}年 {event['location']}"} for event in issue['events']]
    atomic_json(root / 'archives' / f'{issue_date}.json', issue)
    atomic_json(root / 'issue.json', issue)
    atomic_json(root / 'today_news.json', legacy)
    return issue


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--date', default=dt.datetime.now(BEIJING).date().isoformat())
    args = parser.parse_args()
    issue = publish(Path(__file__).resolve().parent, args.date)
    print(f"Published {issue['date']}: {len(issue['events'])} source-reviewed events ({issue['status']})")


if __name__ == '__main__':
    main()  # Exceptions propagate: failed CI must never appear successful.
