"""
주간 브리프 — Telegram HTML 포맷터
- 모든 날짜/시간 KST 기준
- 이모지 없음
- 상단에 모노스페이스 요약표
"""
import json
import html
import re
from datetime import datetime, timedelta
from collections import defaultdict, Counter


# 지표 이름 축약 (테이블 공간 절약)
INDICATOR_ABBREV = {
    'Durable Goods Orders MoM': 'Durable Gds',
    'FOMC Minutes': 'FOMC Minutes',
    'Core PCE Price Index MoM': 'Core PCE MoM',
    'Core PCE Price Index YoY': 'Core PCE YoY',
    'PCE Price Index MoM': 'PCE MoM',
    'PCE Price Index YoY': 'PCE YoY',
    'GDP Growth Rate QoQ Final': 'GDP Q-Final',
    'GDP Growth Rate QoQ Adv': 'GDP Q-Advance',
    'GDP Growth Rate QoQ': 'GDP QoQ',
    'Personal Income MoM': 'Personal Inc',
    'Personal Spending MoM': 'Personal Spd',
    'Core Inflation Rate MoM': 'Core CPI MoM',
    'Core Inflation Rate YoY': 'Core CPI YoY',
    'Inflation Rate MoM': 'CPI MoM',
    'Inflation Rate YoY': 'CPI YoY',
    'Michigan Consumer Sentiment Prel': 'Michigan',
    'Michigan Consumer Sentiment Final': 'Michigan F',
    'Non Farm Payrolls': 'NFP',
    'Unemployment Rate': 'Unemp Rate',
    'Initial Jobless Claims': 'Jobless Clms',
    'JOLTs Job Openings': 'JOLTs',
    'Retail Sales MoM': 'Retail Sales',
    'Core Retail Sales MoM': 'Core Retail',
    'ISM Manufacturing PMI': 'ISM Manu PMI',
    'ISM Services PMI': 'ISM Svc PMI',
    'PPI MoM': 'PPI MoM',
    'Core PPI MoM': 'Core PPI MoM',
    'PPI YoY': 'PPI YoY',
    'Housing Starts': 'Housing Strt',
    'Building Permits': 'Build Permit',
    'Industrial Production MoM': 'Indus Prod',
}


KOR_WEEKDAY = {0: '월', 1: '화', 2: '수', 3: '목', 4: '금', 5: '토', 6: '일'}


def et_to_kst(date_str, time_str):
    """ET 날짜+시간을 KST (date, time, weekday_idx)로 변환"""
    try:
        dt = datetime.strptime(f'{date_str} {time_str}', '%Y-%m-%d %I:%M %p')
        kst = dt + timedelta(hours=13)  # EDT → KST
        return kst.strftime('%Y-%m-%d'), kst.strftime('%H:%M'), kst.weekday()
    except Exception:
        return date_str, '--:--', 0


def esc(text):
    if text is None:
        return ''
    return html.escape(str(text), quote=False)


def extract_number(s):
    """숫자 문자열에서 수치만 추출 (revised 마크 등 제거)"""
    if not s:
        return None
    m = re.search(r'-?\d+\.?\d*', s.replace(',', ''))
    if not m:
        return None
    try:
        return float(m.group())
    except ValueError:
        return None


def clean_value(s):
    """값 문자열 정리 (revised 마크, 줄바꿈 제거)"""
    if not s:
        return '-'
    # 첫 줄만 + 공백 제거 + revised 마크 제거
    s = s.split('\n')[0].strip().replace('®', '').strip()
    return s if s else '-'


def visual_width(s):
    """CJK(한글/한자) 문자는 2, 그 외는 1로 계산"""
    width = 0
    for c in s:
        if ord(c) > 127:
            width += 2
        else:
            width += 1
    return width


def pad_left(s, width):
    """시각적 너비 기준 왼쪽 정렬 (오른쪽 패딩)"""
    pad = max(0, width - visual_width(s))
    return s + ' ' * pad


def format_value_table(event):
    """이벤트당 작은 값 테이블 (인라인, 선 없음)"""
    prev = clean_value(event.get('previous', ''))
    cons = clean_value(event.get('consensus', ''))
    actual = clean_value(event.get('actual', ''))
    forecast = clean_value(event.get('forecast', ''))

    if prev == '-' and cons == '-' and actual == '-' and forecast == '-':
        return ''

    headers = ['이전', '컨센', '실제', 'TE']
    values = [prev, cons, actual, forecast]

    # 컬럼 너비: 헤더와 값 중 최대 + 여백 3
    col_w = max(
        max(visual_width(h) for h in headers),
        max(visual_width(v) for v in values)
    ) + 3

    header_line = ''.join(pad_left(h, col_w) for h in headers).rstrip()
    value_line = ''.join(pad_left(v, col_w) for v in values).rstrip()

    table = f'{header_line}\n{value_line}'
    return f'<pre>{esc(table)}</pre>'


def format_summary_table(events_kst):
    """모노스페이스 요약표 생성 (Telegram <pre> 블록)"""
    if not events_kst:
        return ''

    # 컬럼 너비
    COL_TIME = 9   # "07화21:30" (9 chars)
    COL_NAME = 13  # "Core PCE MoM " (max 13)
    COL_VAL = 5    # "-0.5 " right-aligned

    lines = []
    # 헤더
    header = (
        '일시'.ljust(COL_TIME) + ' ' +
        '지표'.ljust(COL_NAME) + '  ' +
        '이전'.rjust(COL_VAL) + '   →  ' +
        '컨센'.rjust(COL_VAL)
    )
    lines.append(header)
    lines.append('─' * 40)

    for e in events_kst:
        k_date = e['kst_date']
        k_time = e['kst_time']
        wd = KOR_WEEKDAY[e['kst_weekday']]
        day = k_date[8:10]  # "07"
        time_col = f'{day}{wd} {k_time}'.ljust(COL_TIME)

        name = INDICATOR_ABBREV.get(e['event'], e['event'][:COL_NAME])
        name_col = name[:COL_NAME].ljust(COL_NAME)

        # 값 추출
        prev_num = extract_number(e.get('previous', ''))
        cons_num = extract_number(e.get('consensus', ''))
        actual_num = extract_number(e.get('actual', ''))

        def fmt(n):
            if n is None:
                return '  -  '
            return f'{n:5.1f}'

        prev_col = fmt(prev_num)
        cons_col = fmt(cons_num)

        # 마커
        marker = ''
        if actual_num is not None:
            marker = ' *'
        elif prev_num is not None and cons_num is not None:
            if abs(cons_num - prev_num) >= 0.5:
                marker = ' !'

        # FOMC Minutes 같은 값 없는 이벤트
        if e['event'] == 'FOMC Minutes':
            val_col = '   문서 발표'
        else:
            val_col = f'{prev_col}  → {cons_col}{marker}'

        lines.append(f'{time_col} {name_col} {val_col}')

    table_text = '\n'.join(lines)
    # 범례
    legend = '\n\n* 발표 완료   ! 큰 폭 변화 (≥0.5p)'

    return f'<pre>{esc(table_text)}{legend}</pre>'


def convert_events_to_kst(events):
    """각 이벤트에 KST 날짜/시간 추가"""
    for e in events:
        k_date, k_time, k_wday = et_to_kst(e['date'], e['time'])
        e['kst_date'] = k_date
        e['kst_time'] = k_time
        e['kst_weekday'] = k_wday
    return events


def format_header(data, events_kst):
    summary = data.get('weekly_summary', {})

    if not events_kst:
        kst_dates = []
    else:
        kst_dates = sorted(set(e['kst_date'] for e in events_kst))

    # 주차 계산 (KST 기준)
    if kst_dates:
        start_dt = datetime.strptime(kst_dates[0], '%Y-%m-%d')
        week_num = start_dt.isocalendar()[1]
        year = start_dt.year
        week_label = f'{year}년 {week_num}주차'
        date_range = f'{kst_dates[0][5:]}~{kst_dates[-1][5:]}'
    else:
        week_label = '주간'
        date_range = ''

    total_high = len(events_kst)
    total_all = len(data.get('this_week_all', []))

    lines = [
        f'<b>주간 매크로 브리프</b>',
        f'<i>{esc(week_label)} ({esc(date_range)}) · 한국시간(KST)</i>',
        '',
        f'{esc(summary.get("one_liner", ""))}',
        '',
        f'3-star: <b>{total_high}건</b> / 전체: {total_all}건',
    ]

    if summary.get('themes'):
        themes_str = ' · '.join(summary['themes'])
        lines.append(f'테마: {esc(themes_str)}')

    # KST 기준 집중일 재계산
    if events_kst:
        by_kst_date = Counter(e['kst_date'] for e in events_kst)
        busiest_date, busiest_count = max(by_kst_date.items(), key=lambda x: x[1])
        if busiest_count > 1:
            dt = datetime.strptime(busiest_date, '%Y-%m-%d')
            wd = KOR_WEEKDAY[dt.weekday()]
            lines.append(f'집중일: <b>{esc(busiest_date[5:])} ({wd})</b> - {busiest_count}건')

    lines.append('')
    lines.append('────────────────────')
    return '\n'.join(lines)


def format_event(event):
    ins = event.get('insight', {})
    k_date = event['kst_date']
    k_time = event['kst_time']
    wd = KOR_WEEKDAY[event['kst_weekday']]

    event_name = event['event']
    ref = event.get('reference', '')
    ref_str = f' ({esc(ref)})' if ref else ''

    lines = [
        '',
        f'★★★ <b>{esc(event_name)}</b>{ref_str}',
        f'    {esc(k_date[5:])} ({wd}) <code>{esc(k_time)}</code>',
    ]

    # 값 테이블 (인라인)
    value_table = format_value_table(event)
    if value_table:
        lines.append('')
        lines.append(value_table)

    # 해석
    has_interp = bool(ins.get('summary') or ins.get('warnings') or ins.get('context'))
    if value_table and has_interp:
        lines.append('')

    if ins.get('summary'):
        lines.append(f'    {esc(ins["summary"])}')

    for warning in ins.get('warnings', []):
        lines.append(f'    WARN: {esc(warning)}')

    if ins.get('context'):
        lines.append(f'    <i>{esc(ins["context"])}</i>')

    return '\n'.join(lines)


def format_brief(data):
    events = data.get('this_week_high', [])
    events = convert_events_to_kst(events)

    # KST 날짜 기준으로 정렬 + 같은 날짜 내에서는 시간순
    events.sort(key=lambda e: (e['kst_date'], e['kst_time']))

    # KST 날짜별 그룹화
    by_date = defaultdict(list)
    for e in events:
        by_date[e['kst_date']].append(e)

    messages = []
    current_msg = format_header(data, events)
    max_len = 3500

    for date in sorted(by_date.keys()):
        dt = datetime.strptime(date, '%Y-%m-%d')
        wd = KOR_WEEKDAY[dt.weekday()]
        # "- N건" 제거
        date_header = f'\n\n[<b>{esc(date)} ({wd})</b>]'

        if len(current_msg) + len(date_header) > max_len:
            messages.append(current_msg)
            current_msg = date_header.lstrip('\n')
        else:
            current_msg += date_header

        for event in by_date[date]:
            # 이벤트 사이 추가 간격 (엔터 2번)
            event_block = '\n' + format_event(event)
            if len(current_msg) + len(event_block) > max_len:
                messages.append(current_msg)
                current_msg = event_block.lstrip('\n')
            else:
                current_msg += event_block

    footer = '\n\n────────────────────\n<i>자동 생성 | Trading Economics</i>'
    if len(current_msg) + len(footer) > max_len:
        messages.append(current_msg)
        messages.append(footer.lstrip('\n'))
    else:
        current_msg += footer
        messages.append(current_msg)

    return messages


def run():
    print("포맷 시작")
    with open('/Users/machome/weekly-macro-brief/insights.json') as f:
        data = json.load(f)

    messages = format_brief(data)
    print(f"{len(messages)}개 메시지로 분할")

    for i, msg in enumerate(messages):
        print(f"\n{'=' * 40}")
        print(f"메시지 {i+1}/{len(messages)} ({len(msg)}자)")
        print('=' * 40)
        print(msg)

    return messages


if __name__ == '__main__':
    run()
