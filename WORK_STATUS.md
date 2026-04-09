# Weekly Macro Brief — 작업 진행 상태

**최종 업데이트**: 2026-04-09 11:00 KST
**상태**: **전체 파이프라인 완성 + 자동 스케줄 활성화** ✅

---

## 프로젝트 개요

매주/매일 Trading Economics 캘린더에서 미국 3-star 경제지표 **2주치**를 자동 수집하여
HTML 대시보드로 생성하고 Telegram으로 링크 발송하는 시스템.

## 핵심 정보

| 항목 | 값 |
|------|---|
| **로컬 경로** | `/Users/machome/weekly-macro-brief` |
| **GitHub 저장소** | https://github.com/machomehe/weekly-macro-brief (public) |
| **대시보드 URL** | https://machomehe.github.io/weekly-macro-brief/ |
| **경제맵 URL** | https://machomehe.github.io/economic-map/ |
| **Telegram 봇** | `@Eco_Cal_bot` (economic_calendar_bot) |
| **Telegram chat_id** | `8644881596` (Machome) |
| **Telegram 토큰** | `~/weekly-macro-brief/.env` (gitignore됨) |

---

## 자동 스케줄 (launchd, KST 기준)

| 시간 | 작업 | 설명 |
|------|------|------|
| **매일 05:00** | `update` | TE 데이터 수집 → 인사이트 → 대시보드 재생성 → GitHub push |
| **매일 07:00** | `send` | Telegram으로 링크 2개 전송 |
| **매일 12:00** | `send` | Telegram으로 링크 2개 전송 |
| **매일 17:00** | `send` | Telegram으로 링크 2개 전송 |

### launchd 파일 위치
- `~/Library/LaunchAgents/com.machome.weekly-brief-update.plist`
- `~/Library/LaunchAgents/com.machome.weekly-brief-send.plist`

### launchd 관리 명령
```bash
# 상태 확인
launchctl list | grep weekly-brief

# 수동 실행 (테스트)
launchctl start com.machome.weekly-brief-update
launchctl start com.machome.weekly-brief-send

# 중단
launchctl unload ~/Library/LaunchAgents/com.machome.weekly-brief-update.plist
launchctl unload ~/Library/LaunchAgents/com.machome.weekly-brief-send.plist

# 재시작
launchctl load ~/Library/LaunchAgents/com.machome.weekly-brief-update.plist
launchctl load ~/Library/LaunchAgents/com.machome.weekly-brief-send.plist
```

### 로그 위치
- `/tmp/weekly-brief-update.log` — update stdout
- `/tmp/weekly-brief-update.err` — update stderr
- `/tmp/weekly-brief-send.log` — send stdout
- `/tmp/weekly-brief-send.err` — send stderr
- `~/weekly-macro-brief/pipeline.log` — 파이프라인 전체 로그

---

## Telegram 메시지 포맷 (현재 버전)

```
경제 캘린더
https://machomehe.github.io/weekly-macro-brief/

경제맵
https://machomehe.github.io/economic-map/
```

- 다른 문구 없음
- 이름 밑에 링크만
- 탭하면 바로 이동

---

## 완성된 기능

### 1. 데이터 수집 (2주치)
- Playwright + Cloudflare 우회
- 월-금 × 2주 = 10일치 평일 데이터
- US 3-star 지표만 필터

### 2. 대시보드 (HTML)
- 다크 테마, 반응형
- **상단 nav 버튼**: 경제맵 ↔ 캘린더 서로 이동
- **오늘 날짜 강조**: 밝은 테두리 + "오늘" 배지 + 배경 하이라이트
- 지표 제목 클릭 → TE 해당 페이지 이동
- 룰 기반 인사이트 (지표별 색상 코딩)
- 경고/컨텍스트 설명

### 3. Telegram 자동 발송
- 하루 3회 (07:00, 12:00, 17:00 KST)
- 2개 링크를 1개 메시지로
- 텍스트 최소화

### 4. 자동화
- launchd로 완전 무인 운영
- 05:00 데이터 업데이트
- 에러 로깅

---

## 파일 인벤토리

### 핵심 파이프라인
```
~/weekly-macro-brief/
├── run_pipeline.py          # 메인 오케스트레이터 ⭐
├── fetch_calendar.py         # Playwright TE 수집
├── generate_insights.py      # 룰 기반 인사이트
├── generate_dashboard.py     # HTML 생성 (오늘 강조 + nav)
├── calendar.json             # 수집 데이터 (2주치)
├── insights.json             # 인사이트 추가 데이터
├── docs/index.html           # 배포된 대시보드
├── pipeline.log              # 실행 로그
├── .env                      # Telegram 토큰 (gitignore)
├── .gitignore
├── README.md
└── WORK_STATUS.md            # 이 파일
```

### 구 파일 (미사용, 참고용)
- `format_brief.py` — 텔레그램 HTML 포맷터 (현재 미사용)
- `send_telegram.py` — 구버전 브리프 전송 (현재 미사용)
- `send_link.py` — 단일 링크 전송 (현재 미사용, run_pipeline으로 통합)

---

## 수동 실행 (필요 시)

```bash
cd ~/weekly-macro-brief

# 1. 데이터 업데이트 (fetch → insights → dashboard → git push)
python3 run_pipeline.py update

# 2. Telegram 링크 전송
python3 run_pipeline.py send

# 3. 로그 확인
tail -20 pipeline.log
```

---

## 중요 제약사항

1. **맥 전원 상태**: launchd 실행 시간에 맥이 켜져 있거나 수면 모드여야 함
2. **GitHub Actions 불가**: TE가 cloud IP 차단 → 맥 로컬 실행만 가능
3. **`.env` 보안**: Telegram 토큰 절대 커밋 금지
4. **Playwright**: `~/Library/Python/3.9/bin/playwright`
5. **Python**: `/usr/bin/python3` (3.9.6)

---

## 오늘 (2026-04-09) 완료한 작업

1. ✅ `fetch_calendar.py` → 2주치 데이터 수집으로 확장
2. ✅ `generate_dashboard.py` → 오늘 날짜 강조 + 상단 nav 버튼
3. ✅ `run_pipeline.py` → 전체 파이프라인 오케스트레이터 (update/send)
4. ✅ 경제맵 `index.html` → 상단 nav 버튼 추가
5. ✅ Telegram 메시지 포맷 변경 (2개 링크, 1개 메시지)
6. ✅ launchd plist 2개 작성 및 로드
7. ✅ 수동 실행 테스트 성공
8. ✅ GitHub 양쪽 repo 푸시 + Pages 배포 확인

---

## 과거 기록

### 2026-04-08 (Phase 1-3)
- Playwright + TE 데이터 수집
- 룰 기반 인사이트
- HTML 대시보드 + GitHub Pages
- Telegram 봇 통합
- 지표 → TE 링크 연동

### 2026-04-09 (Phase 4-5)
- 2주치 데이터 확장
- 오늘 강조 기능
- 상단 nav 버튼 (양쪽 사이트)
- run_pipeline.py 오케스트레이터
- launchd 자동 스케줄 (1 + 3 schedules)
- **전체 자동화 완성**

---

## 다음 단계 (선택사항, 여유 있으면)

- [ ] 과거 브리프 아카이브 (`docs/archive/YYYY-MM-DD.html`)
- [ ] 에러 발생 시 Telegram으로 실패 알림
- [ ] 중요도 2-star 이벤트도 선택적으로 표시
- [ ] 경제맵과 캘린더 지표 연동 (지표 클릭 → 경제맵에서 해당 노드로 이동)
- [ ] 주간 요약 이메일 (선택)

---

**END OF STATUS DOCUMENT**
