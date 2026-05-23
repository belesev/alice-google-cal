import json
import os
import urllib.parse
import urllib.request
from datetime import datetime, timedelta

CALENDAR_ID = 'primary'
TIMEZONE = os.environ.get('CALENDAR_TIMEZONE', 'Europe/Moscow')

CANCEL_WORDS = {'отмена', 'отменить', 'выход', 'стоп', 'хватит', 'назад'}

MONTHS_RU = [
    'января', 'февраля', 'марта', 'апреля', 'мая', 'июня',
    'июля', 'августа', 'сентября', 'октября', 'ноября', 'декабря',
]


def handler(event, context):
    is_new_session = event.get('session', {}).get('new', False)
    state_bag = event.get('state', {})
    session_state = {} if is_new_session else (
        state_bag.get('session') or state_bag.get('application') or {}
    )

    request = event['request']
    utterance = request.get('original_utterance', '').strip().lower()
    entities = request.get('nlu', {}).get('entities', [])

    def respond(text, new_state, end=False):
        return {
            'version': event['version'],
            'session': event['session'],
            'session_state': new_state,
            'application_state': new_state,
            'response': {
                'text': text,
                'end_session': end,
            },
        }

    if utterance in CANCEL_WORDS:
        return respond('Хорошо, отменила. Если нужно — снова скажи «добавь событие».', {}, end=True)

    step = session_state.get('step', 0)

    # ── Step 0: greet, ask for title ──────────────────────────────────────────
    if step == 0:
        return respond(
            'Привет! Скажи название события, которое добавить в Google Календарь.',
            {'step': 1},
        )

    # ── Step 1: save title, ask for date ─────────────────────────────────────
    if step == 1:
        title = request.get('original_utterance', '').strip()
        if not title:
            return respond('Не расслышала название. Повтори, пожалуйста.', {'step': 1})
        return respond(
            f'«{title}» — отлично. На какую дату?',
            {'step': 2, 'title': title},
        )

    # ── Step 2: save date, ask for time ──────────────────────────────────────
    if step == 2:
        dt_entity = _find_datetime(entities)
        if not dt_entity:
            return respond(
                'Не поняла дату. Скажи, например, «двадцать пятое мая» или «завтра».',
                session_state,
            )
        val = dt_entity['value']
        resolved = _resolve(val)
        date_parts = {'year': resolved.year, 'month': resolved.month, 'day': resolved.day}
        raw = request.get('original_utterance', '').strip()

        # If the user also mentioned the time in the same phrase, finish right away.
        if 'hour' in val:
            state = {**session_state, 'date_said': raw}
            return _finish(event, respond, state, date_parts, resolved, time_said=raw)

        return respond(
            'В котором часу?',
            {**session_state, 'step': 3, 'date': date_parts, 'date_said': raw},
        )

    # ── Step 3: save time, create event ──────────────────────────────────────
    if step == 3:
        dt_entity = _find_datetime(entities)
        if not dt_entity:
            return respond(
                'Не поняла время. Скажи, например, «в три часа дня» или «в 14:00».',
                session_state,
            )
        val = dt_entity['value']
        date_parts = session_state['date']
        base = datetime(date_parts['year'], date_parts['month'], date_parts['day'])
        resolved = _resolve(val, base)
        time_said = request.get('original_utterance', '').strip()
        return _finish(event, respond, session_state, date_parts, resolved, time_said=time_said)

    # Fallback — reset
    return respond('Что-то пошло не так. Начнём заново: скажи название события.', {'step': 1})


# ── helpers ───────────────────────────────────────────────────────────────────

def _find_datetime(entities):
    return next((e for e in entities if e['type'] == 'YANDEX.DATETIME'), None)


def _resolve(val, base=None):
    """Convert a YANDEX.DATETIME value dict to a datetime, handling relative fields."""
    if base is None:
        base = datetime.now()

    result = base

    if 'year' in val:
        result = result.replace(year=result.year + val['year'] if val.get('year_is_relative') else val['year'])
    if 'month' in val:
        if val.get('month_is_relative'):
            m = result.month + val['month']
            result = result.replace(year=result.year + (m - 1) // 12, month=(m - 1) % 12 + 1)
        else:
            result = result.replace(month=val['month'])
    if 'day' in val:
        result = (result + timedelta(days=val['day'])) if val.get('day_is_relative') else result.replace(day=val['day'])
    if 'hour' in val:
        result = (result + timedelta(hours=val['hour'])) if val.get('hour_is_relative') else result.replace(hour=val['hour'], minute=0, second=0, microsecond=0)
    if 'minute' in val:
        result = (result + timedelta(minutes=val['minute'])) if val.get('minute_is_relative') else result.replace(minute=val['minute'], second=0, microsecond=0)
    elif 'hour' in val and not val.get('hour_is_relative'):
        result = result.replace(minute=0, second=0, microsecond=0)

    return result


def _finish(event, respond, session_state, date_parts, resolved, time_said=''):
    title = session_state.get('title', 'Событие')
    start_dt = datetime(date_parts['year'], date_parts['month'], date_parts['day'],
                        resolved.hour, resolved.minute)
    end_dt = start_dt + timedelta(hours=1)
    description = _build_description(event, session_state, time_said)
    try:
        _create_event(title, start_dt, end_dt, description)
    except Exception as exc:
        return respond(f'Не удалось добавить событие: {exc}', {}, end=True)

    day = date_parts['day']
    month_name = MONTHS_RU[date_parts['month'] - 1]
    return respond(
        f'Готово! Добавила «{title}» на {day} {month_name} в {resolved.hour}:{resolved.minute:02d}.',
        {},
        end=True,
    )


def _build_description(event, session_state, time_said):
    sess = event.get('session', {})
    session_id = sess.get('session_id', '—')
    user_id = sess.get('user', {}).get('user_id', sess.get('user_id', '—'))
    skill_id = sess.get('skill_id', '—')
    created_at = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    return '\n'.join([
        'Добавлено навыком Alice',
        f'Время создания: {created_at} ({TIMEZONE})',
        f'Сессия:         {session_id}',
        f'Пользователь:   {user_id}',
        f'Навык:          {skill_id}',
        '',
        'Что было сказано:',
        f'  Название: «{session_state.get("title", "—")}»',
        f'  Дата:     «{session_state.get("date_said", "—")}»',
        f'  Время:    «{time_said or "—"}»',
    ])


def _get_access_token():
    data = urllib.parse.urlencode({
        'client_id':     os.environ['GOOGLE_CLIENT_ID'],
        'client_secret': os.environ['GOOGLE_CLIENT_SECRET'],
        'refresh_token': os.environ['GOOGLE_REFRESH_TOKEN'],
        'grant_type':    'refresh_token',
    }).encode()
    req = urllib.request.Request('https://oauth2.googleapis.com/token', data=data)
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read())['access_token']


def _create_event(title, start_dt, end_dt, description=''):
    token = _get_access_token()
    body = json.dumps({
        'summary':     f'[from Alice] {title}',
        'description': description,
        'start': {'dateTime': start_dt.strftime('%Y-%m-%dT%H:%M:%S'), 'timeZone': TIMEZONE},
        'end':   {'dateTime': end_dt.strftime('%Y-%m-%dT%H:%M:%S'),   'timeZone': TIMEZONE},
    }).encode()
    url = f'https://www.googleapis.com/calendar/v3/calendars/{CALENDAR_ID}/events'
    req = urllib.request.Request(url, data=body, headers={
        'Authorization': f'Bearer {token}',
        'Content-Type': 'application/json',
    })
    urllib.request.urlopen(req)
