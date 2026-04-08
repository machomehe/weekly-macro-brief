# Weekly Macro Brief — 작업 진행 상태

**최종 업데이트**: 2026-04-09 01:00 KST
**다음 작업**: 2026-04-10 예정

---

## 프로젝트 개요

매주 Trading Economics 캘린더에서 미국 3-star 경제지표를 자동 수집하여
HTML 대시보드로 생성하고 Telegram으로 알림 발송하는 시스템.

---

## 핵심 정보

| 항목 | 값 |
|------|---|
| **로컬 경로** | `/Users/machome/weekly-macro-brief` |
| **GitHub 저장소** | https://github.com/machomehe/weekly-macro-brief (public) |
| **대시보드 URL** | https://machomehe.github.io/weekly-macro-brief/ |
| **Telegram 봇 이름** | `@Eco_Cal_bot` (economic_calendar_bot) |
| **Telegram chat_id** | `8644881596` (Machome) |
| **Telegram 토큰** | `~/weekly-macro-brief/.env` (gitignore됨, GitHub에 없음) |

---

## 완료된 작업 (Phase 1-3)

### Phase 1: 데이터 수집 파이프라인 ✅
- **`fetch_calendar.py`** — Playwright로 TE 미국 캘린더 수집
  - 실행: `python3 fetch_calendar.py`
  - 출력: `calendar.json`
  - Cloudflare 통과 확인됨 (실제 브라우저 사용)
  - **중요**: GitHub Actions에서는 차단됨. 맥 로컬에서만 작동.

### Phase 2: 인사이트 생성 ✅
- **`generate_insights.py`** — 룰 기반 지표별 인사이트
  - 실행: `python3 generate_insights.py`
  - 입력: `calendar.json`
  - 출력: `insights.json`
  - 11개 지표에 대해 사전 정의된 임계값 규칙으로 해석 생성
  - 지표: CPI, Core CPI, PCE, GDP, Personal Income/Spending, Durable Goods, Michigan, FOMC Minutes 등

### Phase 3: HTML 대시보드 + Telegram 알림 ✅
- **`generate_dashboard.py`** — 반응형 HTML 생성
  - 실행: `python3 generate_dashboard.py`
  - 입력: `insights.json`
  - 출력: `docs/index.html`
  - 다크 테마, 모바일 반응형
  - 각 지표 제목 클릭 → TE 해당 페이지로 이동 (새 탭)

- **`send_link.py`** — Telegram으로 대시보드 링크 전송
  - 실행: `python3 send_link.py`
  - 사용: `.env` 환경변수 (TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID)

- **GitHub Pages 자동 배포 활성화**
  - 소스: `main` 브랜치 `/docs` 폴더
  - 푸시 후 약 1분 내 자동 배포

---

## 파일 인벤토리

### 소스 코드 (GitHub에 있음)
```
~/weekly-macro-brief/
├── .gitignore              # .env 및 테스트 파일 제외
├── README.md               # 프로젝트 설명
├── WORK_STATUS.md          # 이 파일
├── fetch_calendar.py       # TE 캘린더 수집 (Playwright)
├── generate_insights.py    # 룰 기반 인사이트
├── generate_dashboard.py   # HTML 대시보드 생성
├── format_brief.py         # (구버전) Telegram HTML 포맷 - 현재 미사용
├── send_telegram.py        # (구버전) 전체 브리프 Telegram 전송 - 현재 미사용
├── send_link.py            # (현재 사용) Telegram 링크 전송
├── calendar.json           # 현재 주 TE 데이터 (캐시)
├── insights.json           # 인사이트 추가된 데이터
└── docs/
    └── index.html          # 배포된 대시보드
```

### 로컬 전용 (GitHub에 없음 — .gitignore)
```
.env                        # Telegram 토큰 (보안)
te_test.png                 # 테스트 스크린샷
te_table.png
te_full.png
te_viewport.png
te_raw.html                 # TE 원본 HTML (디버깅용)
te_events.json              # 테스트 이벤트 덤프
test_te*.py                 # 실험용 테스트 스크립트들
brief_preview.md            # 로컬 미리보기
```

---

## 현재 실행 흐름 (수동)

```bash
cd ~/weekly-macro-brief

# 1. TE 데이터 수집 (약 10초)
python3 fetch_calendar.py

# 2. 인사이트 생성 (즉시)
python3 generate_insights.py

# 3. HTML 대시보드 생성 (즉시)
python3 generate_dashboard.py

# 4. GitHub에 커밋 + 푸시
git add docs/index.html calendar.json insights.json
git commit -m "update: weekly brief $(date +%Y-%m-%d)"
git push

# 5. GitHub Pages 재배포 대기 (~1분)
sleep 60

# 6. Telegram 알림 전송
python3 send_link.py
```

---

## 남은 작업 (Phase 4-5) — 내일 진행

### Phase 4: 오케스트레이션 ⬜
- [ ] **`run_pipeline.py`** 작성
  - 위 6단계를 자동으로 순차 실행
  - 각 단계별 에러 처리 (실패 시 어떻게 할지)
  - 로깅 (성공/실패 추적)
  - 예시 구조:
    ```python
    import subprocess
    import sys
    from datetime import datetime

    LOG = '/tmp/weekly-brief.log'

    def log(msg):
        with open(LOG, 'a') as f:
            f.write(f'[{datetime.now()}] {msg}\n')

    def step(name, cmd):
        log(f'START: {name}')
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        if result.returncode != 0:
            log(f'FAIL: {name} — {result.stderr}')
            return False
        log(f'OK: {name}')
        return True

    # 순차 실행
    ```

### Phase 5: 자동 스케줄 (launchd) ⬜
- [ ] **`com.user.weekly-brief.plist`** 작성
  - macOS LaunchAgent
  - 매주 지정된 시간 자동 실행
  - 위치: `~/Library/LaunchAgents/`
- [ ] **결정 필요**: 실행 시간
  - 옵션 A: 월 07:00 KST (아침 출근 전)
  - 옵션 B: 일 22:00 KST (주초 준비)
  - 옵션 C: 월 08:00 KST (출근 시간)
- [ ] **launchd 로드**: `launchctl load ~/Library/LaunchAgents/com.user.weekly-brief.plist`
- [ ] **테스트**: `launchctl start com.user.weekly-brief`

### Phase 6: 개선 (여유 있으면)
- [ ] 과거 브리프 아카이브 (`docs/archive/2026-W15.html` 등)
- [ ] 에러 발생 시 Telegram으로 실패 알림
- [ ] Cleveland Fed Nowcast 추가 통합
- [ ] 지표별 과거 서프라이즈 이력 표시

---

## 알려진 이슈 / 주의사항

1. **Cloudflare**: TE는 GitHub Actions에서 차단됨 → 반드시 **맥 로컬 실행**
2. **맥 전원 상태**: launchd 실행 시간에 맥이 켜져 있거나 수면 모드여야 함
3. **Playwright 경로**: `~/Library/Python/3.9/bin/playwright` (PATH에 없을 수 있음)
4. **Telegram 토큰 보안**: 절대 Git에 커밋하지 말 것. `.gitignore`에 `.env` 확인
5. **HTML 구조 변경**: TE가 HTML 구조 바꾸면 `fetch_calendar.py`의 셀렉터 수정 필요
6. **파이썬 버전**: 시스템 Python 3.9.6 사용 중. `/usr/bin/python3`

---

## 기술적 세부사항 (메모)

### Playwright 설정
- **크로미움 설치 경로**: `~/Library/Caches/ms-playwright/chromium_headless_shell-1208`
- **사용 중인 옵션**:
  ```python
  browser = p.chromium.launch(
      headless=True,
      args=['--disable-blink-features=AutomationControlled', '--no-sandbox']
  )
  context = browser.new_context(
      viewport={'width': 1600, 'height': 1200},
      device_scale_factor=2,
      user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)...',
      locale='en-US',
      timezone_id='America/New_York',
  )
  ```
- **TE URL**: `https://tradingeconomics.com/united-states/calendar`
- **중요 HTML 패턴**:
  - 테이블: `table#calendar`
  - 행: `tr[data-id]`
  - 날짜: `td` 첫 번째 셀의 class (`class=" 2026-04-10"`)
  - 중요도: `span.calendar-date-N` (N=1,2,3)
  - 이벤트명: `a.calendar-event`
  - 값: `#previous`, `#consensus`, `#forecast`, `#actual` (id로 재사용됨)

### Telegram 봇
- **Bot API URL**: `https://api.telegram.org/bot<TOKEN>/sendMessage`
- **parse_mode**: `HTML` 사용 (MarkdownV2는 escape 복잡)
- **메시지 크기 제한**: 4096자

### GitHub Pages
- **저장소 설정**: Settings → Pages → Source: `main`, Folder: `/docs`
- **API 활성화 명령**:
  ```bash
  gh api -X POST repos/machomehe/weekly-macro-brief/pages \
    -f "source[branch]=main" -f "source[path]=/docs"
  ```

---

## 복원 가이드 (터미널 재시작 시)

```bash
# 1. 프로젝트 폴더로 이동
cd ~/weekly-macro-brief

# 2. 현재 상태 확인
cat WORK_STATUS.md
git status
git log --oneline -10

# 3. 수동 실행 테스트 (선택)
python3 fetch_calendar.py && python3 generate_insights.py && python3 generate_dashboard.py
open docs/index.html  # 로컬 미리보기

# 4. 내일 이어서 작업: Phase 4 (run_pipeline.py)
```

---

## Claude에게 내일 전할 프롬프트 (참고)

> "어제 `~/weekly-macro-brief` 프로젝트 하던 거 이어서. WORK_STATUS.md 먼저 읽고,
> Phase 4 `run_pipeline.py` 오케스트레이터 작성부터 시작해줘.
> 그 다음 launchd 자동 스케줄 설정. 실행 시간은 아직 안 정했어."

---

## 오늘 이 대화에서 결정된 사항

1. ✅ **데이터 소스**: Trading Economics (Playwright로 스크래핑, 맥 로컬)
2. ✅ **인사이트 방식**: 룰 기반 (LLM 미사용)
3. ✅ **전달 방법**: Telegram으로 링크만 → 클릭하면 HTML 대시보드
4. ✅ **호스팅**: GitHub Pages (public 저장소, 별도 URL)
5. ✅ **시간대**: 모든 날짜/시간 KST 기준으로 표시
6. ✅ **보안**: `.env`에 토큰 저장, 절대 커밋 금지
7. ⬜ **실행 시간**: 아직 미결정 (월요일 아침 유력)
8. ⬜ **자동화**: launchd로 할 예정, 아직 설정 안 됨

---

## 진행 경과 요약

1. **Playwright 접근 성공** → 맥 로컬에서 Cloudflare 통과 확인
2. **TE 캘린더 파싱 성공** → 286개 이벤트 추출, 이번 주 3-star 11개 필터
3. **KST 시간 변환** → ET + 13시간, 날짜 롤오버 처리 (FOMC Minutes는 수→목 전환)
4. **Telegram 통합 성공** → 봇 생성, 링크 전송 확인
5. **HTML 대시보드 완성** → 다크 테마, 반응형, 지표별 카드
6. **GitHub 배포 완성** → Pages 활성화, 자동 배포 작동
7. **지표 → TE 링크 연동** → 각 이벤트 제목 클릭 시 TE 해당 페이지로 이동

---

**END OF STATUS DOCUMENT**
