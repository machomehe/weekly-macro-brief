"""
주간 브리프 HTML 대시보드 생성기
insights.json → 모바일 친화적 반응형 HTML 페이지
"""
import json
import html
from datetime import datetime, timedelta
from collections import defaultdict, Counter
from pathlib import Path


KOR_WEEKDAY = {0: '월', 1: '화', 2: '수', 3: '목', 4: '금', 5: '토', 6: '일'}


def et_to_kst(date_str, time_str):
    try:
        dt = datetime.strptime(f'{date_str} {time_str}', '%Y-%m-%d %I:%M %p')
        kst = dt + timedelta(hours=13)
        return kst.strftime('%Y-%m-%d'), kst.strftime('%H:%M'), kst.weekday()
    except Exception:
        return date_str, '--:--', 0


def esc(text):
    if text is None:
        return ''
    return html.escape(str(text), quote=True)


def get_impact_class(summary_text):
    """인사이트 summary에서 위험도 클래스 추출"""
    if '[고위험]' in summary_text:
        return 'danger'
    if '[주의]' in summary_text:
        return 'warning'
    if '[양호]' in summary_text or '[완화]' in summary_text:
        return 'success'
    if '[중립]' in summary_text:
        return 'neutral'
    return ''


def generate_html(data):
    events = list(data.get('this_week_high', []))
    # KST 변환
    for e in events:
        k_date, k_time, k_wday = et_to_kst(e['date'], e['time'])
        e['kst_date'] = k_date
        e['kst_time'] = k_time
        e['kst_weekday'] = k_wday

    # 정렬 + 그룹화
    events.sort(key=lambda e: (e['kst_date'], e['kst_time']))
    by_date = defaultdict(list)
    for e in events:
        by_date[e['kst_date']].append(e)

    summary = data.get('weekly_summary', {})

    # 주차 계산
    kst_dates = sorted(by_date.keys())
    if kst_dates:
        start_dt = datetime.strptime(kst_dates[0], '%Y-%m-%d')
        week_num = start_dt.isocalendar()[1]
        year = start_dt.year
        week_label = f'{year}년 {week_num}주차'
        date_range = f'{kst_dates[0][5:]} ~ {kst_dates[-1][5:]}'
    else:
        week_label = '주간'
        date_range = ''

    # KST 기준 집중일
    by_kst = Counter(e['kst_date'] for e in events)
    busiest_info = ''
    if by_kst:
        busiest_date, busiest_count = max(by_kst.items(), key=lambda x: x[1])
        if busiest_count > 1:
            dt_b = datetime.strptime(busiest_date, '%Y-%m-%d')
            busiest_info = f'{busiest_date[5:]} ({KOR_WEEKDAY[dt_b.weekday()]}) · {busiest_count}건'

    fetched = data.get('fetched_at', '')
    if fetched:
        try:
            fetched_dt = datetime.fromisoformat(fetched.replace('Z', '+00:00'))
            fetched_kst = fetched_dt + timedelta(hours=9)
            fetched_str = fetched_kst.strftime('%Y-%m-%d %H:%M KST')
        except Exception:
            fetched_str = fetched
    else:
        fetched_str = '알 수 없음'

    # ============ HTML 렌더링 ============
    date_sections = []
    for date in sorted(by_date.keys()):
        dt = datetime.strptime(date, '%Y-%m-%d')
        wd = KOR_WEEKDAY[dt.weekday()]

        event_cards = []
        for e in by_date[date]:
            ins = e.get('insight', {})
            summary_text = ins.get('summary', '')
            impact_cls = get_impact_class(summary_text)

            # 값 테이블
            prev = e.get('previous', '').split('\n')[0].strip().replace('®', '').strip() or '-'
            cons = e.get('consensus', '').strip() or '-'
            actual = e.get('actual', '').strip() or '-'
            forecast = e.get('forecast', '').strip() or '-'

            table_html = f'''
            <table class="values">
              <thead>
                <tr><th>이전</th><th>컨센</th><th>실제</th><th>TE</th></tr>
              </thead>
              <tbody>
                <tr>
                  <td>{esc(prev)}</td>
                  <td class="consensus">{esc(cons)}</td>
                  <td>{esc(actual)}</td>
                  <td>{esc(forecast)}</td>
                </tr>
              </tbody>
            </table>
            '''

            # 경고
            warnings_html = ''
            if ins.get('warnings'):
                warnings_html = '<div class="warnings">' + ''.join(
                    f'<div class="warning">⚠ {esc(w)}</div>' for w in ins['warnings']
                ) + '</div>'

            # 인사이트 summary + context
            summary_html = ''
            if summary_text:
                summary_html = f'<div class="insight-summary {impact_cls}">{esc(summary_text)}</div>'

            context_html = ''
            if ins.get('context'):
                context_html = f'<div class="context">{esc(ins["context"])}</div>'

            ref = e.get('reference', '')
            ref_str = f'<span class="reference">({esc(ref)})</span>' if ref else ''

            card = f'''
            <div class="event-card">
              <div class="event-header">
                <div class="stars">★★★</div>
                <div class="event-title">
                  <h3>{esc(e['event'])} {ref_str}</h3>
                  <div class="time-badge">{esc(e['kst_time'])} KST</div>
                </div>
              </div>
              {table_html}
              {summary_html}
              {warnings_html}
              {context_html}
            </div>
            '''
            event_cards.append(card)

        section = f'''
        <section class="date-section">
          <h2 class="date-heading">
            <span class="date-label">{esc(date[5:])}</span>
            <span class="weekday">{wd}요일</span>
            <span class="date-count">{len(by_date[date])}건</span>
          </h2>
          {''.join(event_cards)}
        </section>
        '''
        date_sections.append(section)

    # 테마 뱃지
    themes_html = ''
    if summary.get('themes'):
        themes_html = '<div class="themes">' + ''.join(
            f'<span class="theme-badge">{esc(t)}</span>' for t in summary['themes']
        ) + '</div>'

    # 전체 HTML
    html_content = f'''<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0, viewport-fit=cover">
<title>주간 매크로 브리프 · {esc(week_label)}</title>
<style>
* {{ box-sizing: border-box; margin: 0; padding: 0; }}
:root {{
  --bg: #0f0f14;
  --bg-card: #1a1a24;
  --bg-alt: #1e1e2e;
  --text: #e2e8f0;
  --text-dim: #94a3b8;
  --text-muted: #64748b;
  --border: #2a2a3a;
  --accent: #6366f1;
  --success: #22c55e;
  --warning: #f59e0b;
  --danger: #dc2626;
  --neutral: #64748b;
}}
html, body {{
  background: var(--bg);
  color: var(--text);
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Pretendard', Roboto, sans-serif;
  line-height: 1.6;
  padding: env(safe-area-inset-top) env(safe-area-inset-right) env(safe-area-inset-bottom) env(safe-area-inset-left);
  -webkit-font-smoothing: antialiased;
}}
main {{
  max-width: 720px;
  margin: 0 auto;
  padding: 20px 16px 40px;
}}
header.page-header {{
  padding: 24px 0 20px;
  border-bottom: 1px solid var(--border);
  margin-bottom: 24px;
}}
header.page-header h1 {{
  font-size: 22px;
  font-weight: 800;
  color: var(--text);
  margin-bottom: 4px;
  letter-spacing: -0.3px;
}}
header.page-header .subtitle {{
  font-size: 13px;
  color: var(--text-dim);
  margin-bottom: 16px;
}}
.one-liner {{
  font-size: 15px;
  color: var(--text);
  padding: 12px 16px;
  background: linear-gradient(135deg, rgba(99,102,241,0.15), rgba(99,102,241,0.05));
  border-left: 3px solid var(--accent);
  border-radius: 6px;
  margin-bottom: 16px;
}}
.stats {{
  display: flex;
  gap: 12px;
  flex-wrap: wrap;
  font-size: 13px;
  color: var(--text-dim);
  margin-bottom: 12px;
}}
.stats .stat {{
  display: inline-flex;
  align-items: center;
  gap: 4px;
}}
.stats strong {{
  color: var(--text);
  font-size: 15px;
}}
.themes {{
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-top: 8px;
}}
.theme-badge {{
  background: var(--bg-card);
  border: 1px solid var(--border);
  padding: 4px 10px;
  border-radius: 12px;
  font-size: 11px;
  color: var(--text-dim);
}}
.busiest {{
  margin-top: 8px;
  font-size: 12px;
  color: var(--text-muted);
}}
.busiest strong {{
  color: var(--warning);
}}
.date-section {{
  margin-bottom: 32px;
}}
.date-heading {{
  display: flex;
  align-items: baseline;
  gap: 10px;
  padding: 10px 0;
  margin-bottom: 12px;
  border-bottom: 1px solid var(--border);
}}
.date-heading .date-label {{
  font-size: 18px;
  font-weight: 700;
  color: var(--text);
}}
.date-heading .weekday {{
  font-size: 13px;
  color: var(--accent);
  font-weight: 600;
}}
.date-heading .date-count {{
  margin-left: auto;
  font-size: 12px;
  color: var(--text-muted);
}}
.event-card {{
  background: var(--bg-card);
  border: 1px solid var(--border);
  border-radius: 12px;
  padding: 16px;
  margin-bottom: 12px;
  transition: transform 0.15s, border-color 0.15s;
}}
.event-card:hover {{
  border-color: var(--accent);
}}
.event-header {{
  display: flex;
  align-items: flex-start;
  gap: 10px;
  margin-bottom: 12px;
}}
.stars {{
  color: var(--warning);
  font-size: 12px;
  letter-spacing: 1px;
  padding-top: 4px;
  flex-shrink: 0;
}}
.event-title {{
  flex: 1;
  min-width: 0;
}}
.event-title h3 {{
  font-size: 15px;
  font-weight: 700;
  color: var(--text);
  margin-bottom: 4px;
  line-height: 1.35;
}}
.event-title .reference {{
  color: var(--text-muted);
  font-weight: 400;
  font-size: 13px;
}}
.time-badge {{
  display: inline-block;
  font-size: 11px;
  color: var(--text-dim);
  font-family: 'SF Mono', Menlo, monospace;
  background: var(--bg-alt);
  padding: 2px 8px;
  border-radius: 4px;
}}
table.values {{
  width: 100%;
  border-collapse: collapse;
  margin: 10px 0;
  font-family: 'SF Mono', Menlo, Consolas, monospace;
  font-size: 13px;
}}
table.values th {{
  text-align: center;
  padding: 8px 6px;
  font-size: 11px;
  font-weight: 600;
  color: var(--text-muted);
  text-transform: uppercase;
  letter-spacing: 0.5px;
  background: var(--bg-alt);
  border-top: 1px solid var(--border);
  border-bottom: 1px solid var(--border);
}}
table.values td {{
  text-align: center;
  padding: 10px 6px;
  color: var(--text);
  font-weight: 600;
}}
table.values td.consensus {{
  color: var(--accent);
  font-weight: 700;
  background: rgba(99,102,241,0.08);
}}
table.values th:first-child, table.values td:first-child {{ border-radius: 6px 0 0 6px; }}
table.values th:last-child, table.values td:last-child {{ border-radius: 0 6px 6px 0; }}
.insight-summary {{
  font-size: 13px;
  padding: 10px 12px;
  border-radius: 6px;
  margin-top: 10px;
  background: var(--bg-alt);
  border-left: 3px solid var(--neutral);
  color: var(--text);
}}
.insight-summary.danger {{ border-left-color: var(--danger); background: rgba(220,38,38,0.1); }}
.insight-summary.warning {{ border-left-color: var(--warning); background: rgba(245,158,11,0.1); }}
.insight-summary.success {{ border-left-color: var(--success); background: rgba(34,197,94,0.1); }}
.insight-summary.neutral {{ border-left-color: var(--neutral); }}
.warnings {{ margin-top: 8px; }}
.warning {{
  font-size: 12px;
  color: var(--warning);
  padding: 6px 10px;
  background: rgba(245,158,11,0.08);
  border-radius: 4px;
  margin-top: 4px;
}}
.context {{
  font-size: 12px;
  color: var(--text-dim);
  font-style: italic;
  margin-top: 10px;
  padding-top: 8px;
  border-top: 1px dashed var(--border);
  line-height: 1.5;
}}
footer {{
  margin-top: 40px;
  padding: 20px 0;
  border-top: 1px solid var(--border);
  text-align: center;
  font-size: 11px;
  color: var(--text-muted);
}}
footer .source {{ margin-bottom: 4px; }}
@media (max-width: 480px) {{
  main {{ padding: 12px 12px 32px; }}
  header.page-header h1 {{ font-size: 19px; }}
  .event-card {{ padding: 14px 12px; }}
  table.values {{ font-size: 12px; }}
  table.values th, table.values td {{ padding: 8px 4px; }}
}}
</style>
</head>
<body>
<main>
  <header class="page-header">
    <h1>주간 매크로 브리프</h1>
    <div class="subtitle">{esc(week_label)} · {esc(date_range)} · 한국시간(KST)</div>
    <div class="one-liner">{esc(summary.get('one_liner', ''))}</div>
    <div class="stats">
      <span class="stat"><strong>{len(events)}</strong>건 (3-star)</span>
      <span class="stat">/ 전체 {len(data.get('this_week_all', []))}건</span>
    </div>
    {themes_html}
    {f'<div class="busiest">집중일: <strong>{esc(busiest_info)}</strong></div>' if busiest_info else ''}
  </header>

  {''.join(date_sections)}

  <footer>
    <div class="source">자동 생성 · Trading Economics</div>
    <div>데이터 갱신: {esc(fetched_str)}</div>
  </footer>
</main>
</body>
</html>
'''
    return html_content


def run():
    print("HTML 대시보드 생성 시작")
    base = Path(__file__).parent
    with open(base / 'insights.json') as f:
        data = json.load(f)

    html_content = generate_html(data)

    # docs 폴더에 index.html로 저장 (GitHub Pages 관례)
    docs_dir = base / 'docs'
    docs_dir.mkdir(exist_ok=True)

    output = docs_dir / 'index.html'
    output.write_text(html_content, encoding='utf-8')

    size_kb = len(html_content) / 1024
    print(f"저장: {output}")
    print(f"크기: {size_kb:.1f} KB")
    print(f"\n로컬 미리보기: open {output}")


if __name__ == '__main__':
    run()
