# Weekly Macro Brief

미국 경제지표 주간 브리프 자동 생성 + Telegram 푸시 시스템.

## 개요

매주 Trading Economics 캘린더에서 **이번 주 미국 3-star 경제지표**를 추출하고,
각 지표에 대한 인사이트를 생성하여 HTML 대시보드와 Telegram으로 발송합니다.

## 구성

- `fetch_calendar.py` — Playwright로 TE 캘린더 데이터 수집
- `generate_insights.py` — 룰 기반 지표별 인사이트 생성
- `generate_dashboard.py` — HTML 대시보드 생성 (GitHub Pages용)
- `format_brief.py` — Telegram 메시지 포맷 (참고용)
- `send_telegram.py` — Telegram 봇으로 링크 발송
- `docs/index.html` — 최신 주간 브리프 (GitHub Pages)

## 실행 흐름

```
fetch_calendar.py  →  calendar.json
       ↓
generate_insights.py  →  insights.json
       ↓
generate_dashboard.py  →  docs/index.html
       ↓
git push  →  GitHub Pages 자동 배포
       ↓
send_telegram.py  →  링크 알림
```

## 설정

### 1. 의존성 설치

```bash
pip3 install --user playwright
playwright install chromium
```

### 2. 환경변수 (.env)

```
TELEGRAM_BOT_TOKEN=your_bot_token
TELEGRAM_CHAT_ID=your_chat_id
```

## 면책

- 본 브리프는 자동 생성되며 투자 조언이 아닙니다.
- 모든 데이터는 Trading Economics의 공개 캘린더에서 수집됩니다.
- 개인 학습/분석 목적으로만 사용하세요.
