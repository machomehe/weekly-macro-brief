"""
주간 브리프 — 지표별 인사이트 생성 (룰 기반, 이모지 없음)
"""
import json
import re
from datetime import datetime, timedelta


# ═══════════════════════════════════════════════════════════
# 지표별 해석 룰
# ═══════════════════════════════════════════════════════════
INDICATOR_RULES = {
    # 인플레이션
    'Inflation Rate YoY': {
        'thresholds': [
            (4.0, '[고위험] 고인플레 - 긴축 강화 압력 극대화'),
            (3.0, '[주의] 타겟 상당 상회 - 긴축 유지 명분'),
            (2.5, '[중립] 타겟 약간 상회 - 조심스러운 완화'),
            (2.0, '[양호] 타겟 근접 - 완화 여지'),
            (-999, '[완화] 타겟 하회 - 완화 기대'),
        ],
        'context': '연준 공식 타겟 2%. 3% 초과 시 긴축 압력 급상승.',
    },
    'Core Inflation Rate YoY': {
        'thresholds': [
            (3.5, '[고위험] 기조적 인플레 심각 - 구조적 압력'),
            (3.0, '[주의] 기조 물가 여전 높음'),
            (2.5, '[중립] 완만한 하락 추세'),
            (2.0, '[양호] 타겟 근접'),
            (-999, '[완화] 타겟 하회'),
        ],
        'context': 'Core는 식품·에너지 제외. 연준이 실제 정책 결정에 더 중시.',
    },
    'Core PCE Price Index MoM': {
        'thresholds': [
            (0.4, '[고위험] 월간 가속 - 인플레 모멘텀 살아있음'),
            (0.3, '[주의] 높은 수준 유지'),
            (0.2, '[중립] 목표 수준 근접 (연 2.4%)'),
            (0.1, '[양호] 완만한 하락'),
            (-999, '[완화] 디스인플레 진행'),
        ],
        'context': '연준의 공식 인플레이션 타겟 지표. MoM 0.17%가 연 2% 페이스.',
    },

    # GDP
    'GDP Growth Rate QoQ Final': {
        'thresholds': [
            (4.0, '[고위험] 과열 - 금리 인상 압력'),
            (2.5, '[양호] 건강한 성장'),
            (1.0, '[중립] 둔화 진행'),
            (0.0, '[주의] 스태그네이션 경고'),
            (-999, '[고위험] 기술적 침체 (2분기 연속 -시)'),
        ],
        'context': '미국 잠재성장률 약 1.8%. 이를 넘으면 과열, 0 아래는 침체 경고.',
    },

    # 고용·소득
    'Personal Income MoM': {
        'thresholds': [
            (0.5, '[양호] 임금·투자소득 강세'),
            (0.3, '[중립] 정상 수준'),
            (0.1, '[주의] 소득 성장 둔화'),
            (-999, '[고위험] 소득 역성장'),
        ],
        'context': '소득이 소비의 선행지표. 0.3-0.4% 수준이 건강.',
    },
    'Personal Spending MoM': {
        'thresholds': [
            (0.8, '[양호] 강한 소비'),
            (0.4, '[중립] 정상 소비'),
            (0.2, '[주의] 소비 둔화'),
            (-999, '[고위험] 소비 위축'),
        ],
        'context': 'GDP의 70%를 차지. 0.3-0.5% 수준이 건강한 범위.',
    },

    # 소비자 심리
    'Michigan Consumer Sentiment Prel': {
        'thresholds': [
            (90, '[양호] 소비자 낙관'),
            (75, '[중립] 중립'),
            (60, '[주의] 비관 심화'),
            (50, '[고위험] 침체 수준 비관'),
            (-999, '[고위험] 위기 수준'),
        ],
        'context': '100 = 낙관, 50 이하 = 침체 수준. 소비 선행지표.',
    },

    # 내구재
    'Durable Goods Orders MoM': {
        'thresholds': [
            (2.0, '[양호] 투자 강세'),
            (0.5, '[중립] 정상'),
            (0.0, '[주의] 투자 정체'),
            (-1.0, '[고위험] 투자 위축'),
            (-999, '[고위험] 심각한 위축'),
        ],
        'context': '기업 설비투자 선행지표. 변동성 큼 (항공기 주문 영향).',
    },

    # FOMC Minutes
    'FOMC Minutes': {
        'special': 'fomc_minutes',
        'context': '3월 FOMC 회의 상세 내용. 금리 경로, 인플레 평가, 위원 이견 확인.',
    },
}


def parse_number(s):
    if not s or s in ('-', ''):
        return None
    m = re.search(r'-?\d+\.?\d*', s.replace(',', ''))
    if not m:
        return None
    try:
        return float(m.group())
    except ValueError:
        return None


def interpret_value(indicator_name, value):
    rules = INDICATOR_RULES.get(indicator_name, {})
    thresholds = rules.get('thresholds', [])
    if not thresholds or value is None:
        return None
    for threshold, meaning in thresholds:
        if value >= threshold:
            return meaning
    return None


def get_indicator_rule(event_name):
    for rule_name in INDICATOR_RULES:
        if rule_name in event_name or event_name in rule_name:
            return rule_name, INDICATOR_RULES[rule_name]
    return None, None


def generate_insight(event):
    insight = {
        'summary': '',
        'direction': '',
        'magnitude': '',
        'context': '',
        'interpretation': '',
        'warnings': [],
    }

    rule_name, rule = get_indicator_rule(event['event'])

    previous = parse_number(event.get('previous', ''))
    consensus = parse_number(event.get('consensus', ''))
    actual = parse_number(event.get('actual', ''))
    forecast = parse_number(event.get('forecast', ''))

    # 방향 (컨센서스 vs 이전값)
    if previous is not None and consensus is not None:
        diff = consensus - previous
        abs_diff = abs(diff)
        if abs_diff < 0.05:
            insight['direction'] = '변화 없음 예상'
        elif diff > 0:
            insight['direction'] = f'상승 기대 (+{diff:.2f}p)'
        else:
            insight['direction'] = f'하락 예상 ({diff:.2f}p)'

        if abs_diff >= 0.5:
            insight['warnings'].append(f'큰 폭 변화 예상 (이전값 대비 {diff:+.2f}p)')

    # 결과 (발표 완료)
    if actual is not None and consensus is not None:
        surprise = actual - consensus
        if abs(surprise) < 0.05:
            insight['magnitude'] = '예상 부합'
        elif surprise > 0:
            severity = '강한 ' if abs(surprise) >= 0.3 else ''
            insight['magnitude'] = f'{severity}예상 상회 (+{surprise:.2f}p)'
        else:
            severity = '강한 ' if abs(surprise) >= 0.3 else ''
            insight['magnitude'] = f'{severity}예상 하회 ({surprise:.2f}p)'

    # TE 모델 vs 컨센서스
    if forecast is not None and consensus is not None:
        diff_te = forecast - consensus
        if abs(diff_te) >= 0.2:
            insight['warnings'].append(
                f'TE 모델({forecast:.1f})과 컨센서스({consensus:.1f}) 이견 {diff_te:+.1f}p'
            )

    # 값 기반 해석
    if rule:
        insight['context'] = rule.get('context', '')
        if consensus is not None:
            meaning = interpret_value(rule_name, consensus)
            if meaning:
                insight['interpretation'] = meaning
        if actual is not None:
            meaning = interpret_value(rule_name, actual)
            if meaning:
                insight['interpretation'] = meaning

    # FOMC Minutes 특수 처리
    if rule_name == 'FOMC Minutes':
        insight['summary'] = 'FOMC 회의록 발표'
        insight['context'] = rule['context']
        insight['interpretation'] = '값 없음 - 문서 내용 해석 필요 (hawkish/dovish tone)'

    # 전체 요약 한 줄
    parts = []
    if insight['magnitude']:
        parts.append(insight['magnitude'])
    elif insight['direction']:
        parts.append(insight['direction'])
    if insight['interpretation']:
        parts.append(insight['interpretation'])
    insight['summary'] = ' · '.join(parts) if parts else '분석 대상'

    return insight


def generate_weekly_summary(events, week_dates):
    if not events:
        return {'summary': '이번 주 3-star 이벤트 없음', 'stats': {}}

    cpi_events = [e for e in events if 'inflation' in e['event'].lower() or 'cpi' in e['event'].lower()]
    pce_events = [e for e in events if 'pce' in e['event'].lower()]
    gdp_events = [e for e in events if 'gdp' in e['event'].lower()]
    employment_events = [e for e in events if any(kw in e['event'].lower() for kw in ['payroll', 'employment', 'jolts', 'unemployment', 'claims'])]
    fed_events = [e for e in events if 'fomc' in e['event'].lower()]

    themes = []
    if cpi_events:
        themes.append(f"CPI 주간 ({len(cpi_events)}건)")
    if pce_events:
        themes.append(f"PCE 발표 ({len(pce_events)}건)")
    if gdp_events:
        themes.append(f"GDP 발표 ({len(gdp_events)}건)")
    if employment_events:
        themes.append(f"고용 지표 ({len(employment_events)}건)")
    if fed_events:
        themes.append(f"Fed 이벤트 ({len(fed_events)}건)")

    from collections import Counter
    by_date = Counter(e['date'] for e in events)
    busiest_date = max(by_date.items(), key=lambda x: x[1]) if by_date else (None, 0)

    if cpi_events and gdp_events:
        one_liner = "CPI + GDP 동시 발표 - 인플레와 성장 모두 확인 주간"
    elif cpi_events:
        one_liner = "CPI 발표 주간 - 인플레 경로 확인"
    elif employment_events:
        one_liner = "고용 지표 주간"
    elif fed_events:
        one_liner = "Fed 이벤트 주간 - 정책 방향 단서"
    elif pce_events:
        one_liner = "PCE 발표 주간 - 연준 공식 인플레 타겟"
    else:
        one_liner = f"일반 주간 ({len(events)}건)"

    return {
        'one_liner': one_liner,
        'themes': themes,
        'total': len(events),
        'busiest_day': busiest_date[0] if busiest_date[1] > 1 else None,
        'busiest_count': busiest_date[1],
    }


def run():
    print("인사이트 생성 시작")

    with open('/Users/machome/weekly-macro-brief/calendar.json') as f:
        data = json.load(f)

    events = data.get('this_week_high', [])
    print(f"입력: {len(events)}개 이벤트")

    for event in events:
        event['insight'] = generate_insight(event)

    summary = generate_weekly_summary(events, data.get('this_week', []))

    output = {
        **data,
        'this_week_high': events,
        'weekly_summary': summary,
    }
    with open('/Users/machome/weekly-macro-brief/insights.json', 'w') as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"\n{'=' * 60}")
    print(f"  {summary['one_liner']}")
    print(f"{'=' * 60}")
    print(f"  주요 테마: {', '.join(summary['themes'])}")
    if summary['busiest_day']:
        print(f"  집중일: {summary['busiest_day']} ({summary['busiest_count']}건)")
    print(f"{'=' * 60}\n")

    for event in events:
        ins = event['insight']
        print(f"  - {event['event']} ({event['reference']}) - {event['date']} {event['time']}")
        print(f"    {ins['summary']}")
        if ins['warnings']:
            for w in ins['warnings']:
                print(f"    WARN: {w}")
        if ins['context']:
            print(f"    {ins['context']}")
        print()

    print(f"insights.json 저장")


if __name__ == '__main__':
    run()
