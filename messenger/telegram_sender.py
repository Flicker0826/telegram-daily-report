"""텔레그램 봇 메시지 전송"""
import requests
import config

TELEGRAM_API = f"https://api.telegram.org/bot{config.TELEGRAM_BOT_TOKEN}"


def send_message(text: str, parse_mode: str = "Markdown") -> bool:
    """
    텔레그램 메시지 전송
    텔레그램 메시지 길이 제한: 4096자
    → 초과 시 분할 전송
    """
    if not config.TELEGRAM_BOT_TOKEN or not config.TELEGRAM_CHAT_ID:
        print("[Telegram] 토큰 또는 Chat ID가 설정되지 않았습니다.")
        return False

    chunks = _split_message(text, max_length=4000)
    success = True

    for chunk in chunks:
        try:
            resp = requests.post(
                f"{TELEGRAM_API}/sendMessage",
                json={
                    "chat_id": config.TELEGRAM_CHAT_ID,
                    "text": chunk,
                    "parse_mode": parse_mode,
                    "disable_web_page_preview": True,
                },
                timeout=30,
            )
            if resp.status_code != 200:
                # Markdown 파싱 실패 시 일반 텍스트로 재시도
                resp2 = requests.post(
                    f"{TELEGRAM_API}/sendMessage",
                    json={
                        "chat_id": config.TELEGRAM_CHAT_ID,
                        "text": chunk,
                        "disable_web_page_preview": True,
                    },
                    timeout=30,
                )
                if resp2.status_code != 200:
                    print(f"[Telegram] 전송 실패: {resp2.text}")
                    success = False
        except Exception as e:
            print(f"[Telegram] 전송 오류: {e}")
            success = False

    return success


def _split_message(text: str, max_length: int = 4000) -> list[str]:
    """긴 메시지를 분할"""
    if len(text) <= max_length:
        return [text]

    chunks = []
    lines = text.split("\n")
    current = ""

    for line in lines:
        if len(current) + len(line) + 1 > max_length:
            if current:
                chunks.append(current)
            current = line
        else:
            current = f"{current}\n{line}" if current else line

    if current:
        chunks.append(current)

    return chunks


def send_error_alert(error_msg: str) -> bool:
    """에러 발생 시 알림 전송"""
    text = f"⚠️ *Daily Report 오류*\n\n```\n{error_msg[:3000]}\n```"
    return send_message(text)
