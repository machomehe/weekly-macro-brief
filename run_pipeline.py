"""
Weekly Macro Brief - 파이프라인 오케스트레이터

사용법:
    python3 run_pipeline.py update  # TE 수집 → 인사이트 → 대시보드 → git push
    python3 run_pipeline.py send    # Telegram 링크 전송 (경제 캘린더 + 경제맵)
"""
import os
import sys
import subprocess
import json
import urllib.request
import urllib.parse
from datetime import datetime
from pathlib import Path


BASE = Path(__file__).parent
LOG_FILE = BASE / 'pipeline.log'

CALENDAR_URL = 'https://machomehe.github.io/weekly-macro-brief/'
MAP_URL = 'https://machomehe.github.io/economic-map/'

# 실행 시 필요한 PATH (launchd 환경에서 python3, git, playwright 찾기 위함)
EXTRA_PATH = '/Users/machome/Library/Python/3.9/bin:/usr/local/bin:/usr/bin:/bin'


def log(msg):
    ts = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    line = f'[{ts}] {msg}\n'
    print(line, end='')
    with open(LOG_FILE, 'a') as f:
        f.write(line)


def load_env():
    env_path = BASE / '.env'
    if not env_path.exists():
        return
    with open(env_path) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                k, v = line.split('=', 1)
                os.environ[k.strip()] = v.strip()


def run_script(name):
    """Python 스크립트 실행"""
    log(f'START: {name}')
    env = os.environ.copy()
    env['PATH'] = EXTRA_PATH + ':' + env.get('PATH', '')
    result = subprocess.run(
        ['/usr/bin/python3', str(BASE / name)],
        capture_output=True,
        text=True,
        cwd=str(BASE),
        env=env,
        timeout=180,
    )
    if result.returncode == 0:
        log(f'OK:    {name}')
        return True
    log(f'FAIL:  {name}')
    log(f'STDERR: {result.stderr[:500]}')
    return False


def git_commit_push():
    """변경사항 커밋 + 푸시"""
    log('Git: commit + push 시도')
    try:
        env = os.environ.copy()
        env['PATH'] = EXTRA_PATH + ':' + env.get('PATH', '')

        subprocess.run(
            ['git', 'add', 'docs/index.html', 'calendar.json', 'insights.json'],
            cwd=str(BASE), env=env, check=True
        )
        # 변경 없으면 스킵
        result = subprocess.run(
            ['git', 'diff', '--cached', '--quiet'],
            cwd=str(BASE), env=env
        )
        if result.returncode == 0:
            log('Git: 변경사항 없음, 스킵')
            return True

        today = datetime.now().strftime('%Y-%m-%d %H:%M')
        subprocess.run(
            ['git', 'commit', '-m', f'update: daily refresh {today}'],
            cwd=str(BASE), env=env, check=True
        )
        subprocess.run(
            ['git', 'push'],
            cwd=str(BASE), env=env, check=True,
            timeout=60,
        )
        log('Git: push OK')
        return True
    except subprocess.CalledProcessError as e:
        log(f'Git 에러: {e}')
        return False
    except subprocess.TimeoutExpired:
        log('Git: push 타임아웃')
        return False


def update():
    """매일 05:00 — 데이터 수집 → 대시보드 재생성 → GitHub 푸시"""
    log('===== UPDATE START =====')
    steps = [
        ('fetch_calendar.py', 'TE 데이터 수집'),
        ('generate_insights.py', '인사이트 생성'),
        ('generate_dashboard.py', 'HTML 대시보드 생성'),
    ]
    for script, desc in steps:
        if not run_script(script):
            log(f'===== UPDATE FAIL at {desc} =====')
            return False

    if not git_commit_push():
        log('===== UPDATE FAIL at git push =====')
        return False

    log('===== UPDATE DONE =====')
    return True


def send_telegram_links():
    """매일 07/12/17시 — Telegram으로 2개 링크 전송 (1개 메시지)"""
    log('===== SEND START =====')
    load_env()
    token = os.environ.get('TELEGRAM_BOT_TOKEN')
    chat_id = os.environ.get('TELEGRAM_CHAT_ID')

    if not token or not chat_id:
        log('TELEGRAM 환경변수 없음')
        return False

    # 메시지: 이름 밑에 링크만, 다른 문구 없음, 2개를 하나의 메시지로
    text = (
        f'경제 캘린더\n'
        f'{CALENDAR_URL}\n'
        f'\n'
        f'경제맵\n'
        f'{MAP_URL}'
    )

    url = f'https://api.telegram.org/bot{token}/sendMessage'
    data = urllib.parse.urlencode({
        'chat_id': chat_id,
        'text': text,
        'disable_web_page_preview': 'true',
    }).encode()

    try:
        req = urllib.request.Request(url, data=data)
        with urllib.request.urlopen(req, timeout=15) as resp:
            result = json.loads(resp.read())
            if result.get('ok'):
                log('===== SEND OK =====')
                return True
            log(f'Telegram 실패: {result}')
            return False
    except Exception as e:
        log(f'Telegram 에러: {e}')
        return False


def main():
    action = sys.argv[1] if len(sys.argv) > 1 else 'send'
    if action == 'update':
        success = update()
    elif action == 'send':
        success = send_telegram_links()
    else:
        log(f'Unknown action: {action}')
        print(f'사용법: python3 {Path(__file__).name} [update|send]')
        success = False
    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()
