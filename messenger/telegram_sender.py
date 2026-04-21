"""텔레그램 봇 메시지 전송 (분할 전송 + Markdown 안전 처리)"""
import re
import time
import requests
import config

TELEGRAM_API = f"https://api.telegram.org/bot{config.TELEGRAM_BOT_TOKEN}"


def send_message(text: str, parse_mode: str = "Markdown") -> bool:
    """
    텔레그램 메시지 전송
    - 4096자 초과 시 구분선(───) 기준 또는 줄 단위로 분할
    - 각 청크의 Markdown을 안전하게 처리
    - 실패 시 일반 텍스트로 재시도
    """
    if not config.TELEGRAM_BOT_TOKEN or not config.TELEGRAM_CHAT_ID:
        print("[Telegram] 토큰 또는 Chat ID가 설정되지 않았습니다.")
        return False

    chunks = _split_message(text, max_length=3800)
    print(f"  📨 메시지 {len(chunks)}개로 분할 전송")
    success = True

    for i, chunk in enumerate(chunks, 1):
        # Markdown 깨짐 방지: 열린 마크다운 닫아주기
        safe_chunk = _fix_markdown(chunk)

        sent = _send_single(safe_chunk, parse_mode, label=f"[{i}/{len(chunks)}]")
        if not sent:
            success = False

        # 청크 사이 딜레이 (Telegram rate limit 방지)
        if i < len(chunks):
            time.sleep(1)

    return success


def _send_single(text: str, parse_mode: str, label: str = "") -> bool:
    """단일 메시지 전송 (Markdown 실패 시 일반 텍스트 재시도)"""
    try:
        # 1차: Markdown으로 시도
        resp = requests.post(
            f"{TELEGRAM_API}/sendMessage",
            json={
                "chat_id": config.TELEGRAM_CHAT_ID,
                "text": text,
                "parse_mode": parse_mode,
                "disable_web_page_preview": True,
            },
            timeout=30,
        )

        if resp.status_code == 200:
            print(f"  ✅ {label} 전송 성공 ({len(text)}자)")
            return True

        # Markdown 파싱 에러 (400) → 일반 텍스트로 재시도
        error_msg = resp.json().get("description", "")
        print(f"  ⚠️ {label} Markdown 실패: {error_msg[:100]}")

        # 2차: 일반 텍스트로 재시도
        resp2 = requests.post(
            f"{TELEGRAM_API}/sendMessage",
            json={
                "chat_id": config.TELEGRAM_CHAT_ID,
                "text": text,
                "disable_web_page_preview": True,
            },
            timeout=30,
        )

        if resp2.status_code == 200:
            print(f"  ✅ {label} 일반 텍스트로 전송 성공")
            return True
        else:
            print(f"  ❌ {label} 전송 최종 실패: {resp2.text[:200]}")
            return False

    except Exception as e:
        print(f"  ❌ {label} 전송 오류: {e}")
        return False


def _fix_markdown(text: str) -> str:
    """
    Markdown 깨짐 방지:
    - 홀수 개의 *가 있으면 마지막 *를 제거
    - 열린 ``` 코드블록 닫기
    """
    # * 개수가 홀수면 마지막 * 제거 (unclosed bold/italic 방지)
    asterisk_count = text.count("*")
    if asterisk_count % 2 != 0:
        # 마지막 * 위치를 찾아서 제거
        last_pos = text.rfind("*")
        text = text[:last_pos] + text[last_pos + 1:]

    # ``` 코드블록이 열려있으면 닫기
    backtick_count = text.count("```")
    if backtick_count % 2 != 0:
        text += "\n```"

    # _ 개수가 홀수면 마지막 _ 제거 (unclosed italic 방지)
    underscore_count = text.count("_")
    if underscore_count % 2 != 0:
        last_pos = text.rfind("_")
        text = text[:last_pos] + text[last_pos + 1:]

    return text


def _split_message(text: str, max_length: int = 3800) -> list[str]:
    """
    긴 메시지를 분할
    1차: 구분선(───) 기준
    2차: 빈 줄 기준
    3차: 줄 단위
    """
    if len(text) <= max_length:
        return [text]

    # 구분선(───)이 있으면 그 기준으로 먼저 나누기
    divider = "─" * 28
    if divider in text:
        parts = text.split(divider)
        chunks = []
        current = ""
        for part in parts:
            candidate = f"{current}{divider}{part}" if current else part
            if len(candidate) <= max_length:
                current = candidate
            else:
                if current:
                    chunks.append(current.strip())
                current = part
        if current:
            chunks.append(current.strip())

        # 각 청크가 여전히 길면 줄 단위로 재분할
        result = []
        for chunk in chunks:
            if len(chunk) <= max_length:
                result.append(chunk)
            else:
                result.extend(_split_by_lines(chunk, max_length))
        return result

    # 구분선이 없으면 줄 단위로 분할
    return _split_by_lines(text, max_length)


def _split_by_lines(text: str, max_length: int) -> list[str]:
    """줄 단위로 분할"""
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
    text = f"⚠️ Daily Report 오류\n\n{error_msg[:3000]}"
    return send_message(text, parse_mode="")
