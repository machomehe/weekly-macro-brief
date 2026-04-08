"""
Telegram 봇으로 주간 브리프 발송
"""
import os
import json
import time
import urllib.request
import urllib.parse
from pathlib import Path

from format_brief import format_brief


def load_env():
    """.env 파일에서 환경변수 로드"""
    env_path = Path(__file__).parent / '.env'
    if env_path.exists():
        with open(env_path) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    os.environ[key.strip()] = value.strip()


def send_message(token, chat_id, text, parse_mode='HTML'):
    """Telegram sendMessage API 호출"""
    url = f'https://api.telegram.org/bot{token}/sendMessage'
    data = urllib.parse.urlencode({
        'chat_id': chat_id,
        'text': text,
        'parse_mode': parse_mode,
        'disable_web_page_preview': 'true',
    }).encode()

    req = urllib.request.Request(url, data=data)
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            result = json.loads(resp.read())
            return result.get('ok', False), result
    except urllib.error.HTTPError as e:
        error_body = e.read().decode()
        return False, {'error': str(e), 'body': error_body}
    except Exception as e:
        return False, {'error': str(e)}


def run():
    load_env()
    token = os.environ.get('TELEGRAM_BOT_TOKEN')
    chat_id = os.environ.get('TELEGRAM_CHAT_ID')

    if not token or not chat_id:
        print("❌ TELEGRAM_BOT_TOKEN / TELEGRAM_CHAT_ID 환경변수 없음")
        return False

    print(f"🚀 Telegram 전송 시작 (chat_id={chat_id})")

    # insights.json 로드
    with open(Path(__file__).parent / 'insights.json') as f:
        data = json.load(f)

    # 메시지 생성
    messages = format_brief(data)
    print(f"📨 {len(messages)}개 메시지 전송 예정")

    # 순차 전송 (Telegram rate limit 대비 0.5초 간격)
    success_count = 0
    for i, msg in enumerate(messages):
        print(f"  [{i+1}/{len(messages)}] 전송 중 ({len(msg)}자)...")
        ok, result = send_message(token, chat_id, msg)
        if ok:
            print(f"    ✅ 성공")
            success_count += 1
        else:
            print(f"    ❌ 실패: {result}")
            # 실패한 메시지 저장
            with open(f'/tmp/failed_msg_{i}.txt', 'w') as f:
                f.write(msg)
            print(f"    💾 실패 메시지 저장: /tmp/failed_msg_{i}.txt")

        if i < len(messages) - 1:
            time.sleep(0.5)

    print(f"\n{'✅' if success_count == len(messages) else '⚠️'} 완료: {success_count}/{len(messages)}")
    return success_count == len(messages)


if __name__ == '__main__':
    import sys
    success = run()
    sys.exit(0 if success else 1)
