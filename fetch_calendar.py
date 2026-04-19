"""
Finnhub 미국 경제 캘린더 수집
- Playwright 스크래핑 → Finnhub API로 교체
- 기존 calendar.json 포맷 유지 (generate_insights.py 호환)
- 2주치 평일, US only, importance 매핑
"""
import os
import json
import requests
from datetime import datetime, timedelta, timezone

# .env 수동 로드 (dotenv 없이도 동작)
ENV_PATH = os.path.join(os.path.dirname(__file__), '.env')
if os.path.exists(ENV_PATH):
    with open(ENV_PATH) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                k, v = line.split('=', 1)
                os.environ.setdefault(k.strip(), v.strip())

API_KEY = os.environ.get('FINNHUB_API_KEY', '')
BASE_URL = 'https://finnhub.io/api/v1'

IMPACT_MAP = {'high': 3, 'medium': 2, 'low': 1}


def get_two_weeks_dates(ref_date=None):
    """이번 주 월요일부터 2주치 평일 반환 (월-금 × 2주, ET 기준)"""
    if ref_date is None:
        ref_date = datetime.now(timezone.utc)
    et_date = ref_date - timedelta(hours=4)  # EDT
    monday = et_date - timedelta(days=et_date.weekday())
    dates = []
    for i in range(14):
        d = monday + timedelta(days=i)
        if d.weekday() < 5:
            dates.append(d.strftime('%Y-%m-%d'))
    return dates


def utc_to_et(utc_str):
    """UTC 시간 문자열 → ET 날짜 + AM/PM 시간"""
    try:
        dt_utc = datetime.strptime(utc_str, '%Y-%m-%d %H:%M:%S')
        dt_et = dt_utc - timedelta(hours=4)  # EDT (4-10월)
        date_str = dt_et.strftime('%Y-%m-%d')
        time_str = dt_et.strftime('%I:%M %p')  # "08:30 AM"
        return date_str, time_str
    except Exception:
        return utc_str[:10] if utc_str else '', ''


def fmt_value(val, unit=''):
    """숫자 → 문자열 (None이면 빈 문자열)"""
    if val is None:
        return ''
    if isinstance(val, (int, float)):
        # 소수점 불필요하면 정수로
        if val == int(val) and abs(val) >= 10:
            return f'{int(val)}'
        return f'{val}'
    return str(val)


def fetch_finnhub_calendar(from_date, to_date):
    """Finnhub 경제 캘린더 API 호출"""
    resp = requests.get(
        f'{BASE_URL}/calendar/economic',
        params={'from': from_date, 'to': to_date, 'token': API_KEY},
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json().get('economicCalendar', [])


def run():
    print('🚀 Finnhub 경제 캘린더 수집 시작')

    # 2주치 날짜 범위
    this_week = get_two_weeks_dates()
    from_date = this_week[0]
    to_date = this_week[-1]
    print(f'📅 범위 (ET): {from_date} ~ {to_date}')

    # API 호출
    raw_events = fetch_finnhub_calendar(from_date, to_date)
    print(f'📊 전체 {len(raw_events)}개 수신')

    # US만 필터 + 공휴일 제외 (estimate/prev/actual 하나라도 있어야)
    us_events = [
        e for e in raw_events
        if e.get('country') == 'US'
        and (e.get('estimate') is not None or e.get('prev') is not None or e.get('actual') is not None)
    ]
    print(f'🇺🇸 US 이벤트 (공휴일 제외): {len(us_events)}개')

    # 기존 calendar.json 포맷으로 변환
    this_week_set = set(this_week)
    all_events = []
    for e in us_events:
        date_str, time_str = utc_to_et(e.get('time', ''))
        importance = IMPACT_MAP.get(e.get('impact', ''), 1)

        event = {
            'date': date_str,
            'time': time_str,
            'importance': importance,
            'event': e.get('event', ''),
            'reference': '',
            'actual': fmt_value(e.get('actual')),
            'previous': fmt_value(e.get('prev')),
            'consensus': fmt_value(e.get('estimate')),
            'forecast': '',
            'category': '',
            'symbol': '',
            'url': '',
        }

        if date_str in this_week_set:
            all_events.append(event)

    # importance별 분리
    high_events = [e for e in all_events if e['importance'] == 3]
    all_events.sort(key=lambda e: (e['date'], e['time']))
    high_events.sort(key=lambda e: (e['date'], e['time']))

    print(f'\n🎯 2주치 전체: {len(all_events)}개')
    print(f'🔴 2주치 3-star: {len(high_events)}개')

    for e in high_events:
        print(f"\n⭐⭐⭐ {e['date']} {e['time']}")
        print(f"   📊 {e['event']}")
        print(f"   이전값: {e['previous'] or '-'}")
        print(f"   컨센서스: {e['consensus'] or '-'}")
        print(f"   Actual: {e['actual'] or '(미발표)'}")

    # 저장 (기존 포맷 유지)
    output = {
        'fetched_at': datetime.now(timezone.utc).isoformat(),
        'source': 'finnhub.io (US economic calendar)',
        'this_week': this_week,
        'total_events': len(raw_events),
        'this_week_high': high_events,
        'this_week_all': all_events,
    }

    output_path = os.path.join(os.path.dirname(__file__), 'calendar.json')
    with open(output_path, 'w') as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    print(f'\n💾 calendar.json 저장')
    print('\n✅ 완료')


if __name__ == '__main__':
    run()
