"""
TE 미국 경제 캘린더 추출 — 최종 버전
- 미국 지표만 (URL)
- 이번 주 필터 (Monday ~ Friday in ET)
- 중요도 필터 가능 (calendar-date-3 = high)
- 정확한 셀 추출 (#actual, #previous, #consensus, #forecast)
- 날짜는 td class에서 추출 (YYYY-MM-DD)
"""
from playwright.sync_api import sync_playwright
from datetime import datetime, timedelta, timezone
import json
import re


def get_this_week_dates(ref_date=None):
    """현재 주의 월~금 날짜 리스트 (ET 기준)"""
    if ref_date is None:
        ref_date = datetime.now(timezone.utc)
    # ET는 UTC-4 또는 UTC-5. 단순화: UTC-4 가정 (summer time)
    et_date = ref_date - timedelta(hours=4)
    monday = et_date - timedelta(days=et_date.weekday())
    return [(monday + timedelta(days=i)).strftime('%Y-%m-%d') for i in range(5)]


def extract_events(page):
    """JavaScript로 캘린더 이벤트 전체 추출"""
    return page.evaluate("""
        () => {
            const table = document.querySelector('table#calendar');
            if (!table) return [];
            const rows = table.querySelectorAll('tr[data-id]');
            const events = [];

            for (const row of rows) {
                // 날짜 추출 (td의 class에서 YYYY-MM-DD 패턴)
                let date = '';
                let importance = 0;
                let time = '';

                const tds = row.querySelectorAll('td');
                if (tds.length === 0) continue;

                // 첫 번째 td: 날짜 클래스 + 시간 + importance
                const firstTd = tds[0];
                const firstClass = firstTd.className || '';
                const dateMatch = firstClass.match(/(\\d{4}-\\d{2}-\\d{2})/);
                if (dateMatch) date = dateMatch[1];

                // 시간
                const timeSpan = firstTd.querySelector('span');
                if (timeSpan) {
                    time = timeSpan.textContent.trim();
                    // importance: calendar-date-N
                    const impMatch = (timeSpan.className || '').match(/calendar-date-(\\d)/);
                    if (impMatch) importance = parseInt(impMatch[1]);
                }

                // 이벤트 이름
                const eventLink = row.querySelector('a.calendar-event');
                const eventName = eventLink ? eventLink.textContent.trim() : '';

                // 참조 기간 (MAR, FEB, etc.)
                const refSpan = row.querySelector('span.calendar-reference');
                const reference = refSpan ? refSpan.textContent.trim() : '';

                // 값들: span#actual, #previous, #consensus, a#forecast
                const actual = (row.querySelector('#actual')?.textContent || '').trim();
                const previous = (row.querySelector('#previous')?.textContent || '').trim();
                const consensus = (row.querySelector('#consensus')?.textContent || '').trim();
                const forecast = (row.querySelector('#forecast')?.textContent || '').trim();

                // 메타데이터
                const dataUrl = row.getAttribute('data-url') || '';
                const category = row.getAttribute('data-category') || '';
                const symbol = row.getAttribute('data-symbol') || '';

                events.push({
                    date,
                    time,
                    importance,  // 1=low, 2=medium, 3=high
                    event: eventName,
                    reference,
                    actual,
                    previous,
                    consensus,
                    forecast,
                    category,
                    symbol,
                    url: dataUrl ? 'https://tradingeconomics.com' + dataUrl : '',
                });
            }
            return events;
        }
    """)


def run():
    print("🚀 시작")

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=['--disable-blink-features=AutomationControlled', '--no-sandbox']
        )
        context = browser.new_context(
            viewport={'width': 1600, 'height': 1200},
            device_scale_factor=2,
            user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
            locale='en-US',
            timezone_id='America/New_York',
        )
        page = context.new_page()

        page.goto(
            'https://tradingeconomics.com/united-states/calendar',
            wait_until='domcontentloaded',
            timeout=30000,
        )
        try:
            page.wait_for_load_state('networkidle', timeout=10000)
        except:
            pass
        page.wait_for_timeout(2000)

        # 모든 이벤트 추출
        events = extract_events(page)
        print(f"📊 전체 {len(events)}개 이벤트 추출")

        # 이번 주 날짜
        this_week = get_this_week_dates()
        print(f"📅 이번 주 (ET): {this_week[0]} ~ {this_week[-1]}")

        # 필터: 이번 주 + high importance만
        this_week_set = set(this_week)
        filtered_high = [
            e for e in events
            if e['date'] in this_week_set and e['importance'] == 3
        ]
        filtered_all = [
            e for e in events
            if e['date'] in this_week_set
        ]

        print(f"\n🎯 이번 주 전체: {len(filtered_all)}개")
        print(f"🔴 이번 주 3-star: {len(filtered_high)}개")

        # 이번 주 3-star 출력
        print(f"\n=== 이번 주 3-star 미국 경제지표 ===")
        for e in filtered_high:
            imp_star = '⭐' * e['importance']
            print(f"\n{imp_star} {e['date']} {e['time']}")
            print(f"   📊 {e['event']} ({e['reference']})")
            print(f"   이전값: {e['previous'] or '-'}")
            print(f"   컨센서스: {e['consensus'] or '-'}")
            print(f"   Actual: {e['actual'] or '(미발표)'}")
            print(f"   TE 전망: {e['forecast'] or '-'}")

        # 저장
        output = {
            'fetched_at': datetime.now(timezone.utc).isoformat(),
            'source': 'tradingeconomics.com/united-states/calendar',
            'this_week': this_week,
            'total_events': len(events),
            'this_week_high': filtered_high,
            'this_week_all': filtered_all,
        }
        with open('/Users/machome/weekly-macro-brief/calendar.json', 'w') as f:
            json.dump(output, f, ensure_ascii=False, indent=2)
        print(f"\n💾 calendar.json 저장")

        browser.close()
        print("\n✅ 완료")


if __name__ == '__main__':
    run()
