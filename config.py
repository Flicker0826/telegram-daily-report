"""환경변수 및 설정 관리"""
import os
import json
import tempfile

# === Telegram ===
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")

# === Gemini ===
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")

# === Google Sheets ===
GOOGLE_SHEET_ID = os.getenv("GOOGLE_SHEET_ID", "")
GOOGLE_SHEETS_CREDS = os.getenv("GOOGLE_SHEETS_CREDS", "")  # JSON string

def get_google_creds_path() -> str:
    """GitHub Secrets의 JSON 문자열을 임시 파일로 저장하고 경로 반환"""
    if os.path.exists("credentials.json"):
        return "credentials.json"
    if GOOGLE_SHEETS_CREDS:
        tmp = tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False)
        tmp.write(GOOGLE_SHEETS_CREDS)
        tmp.close()
        return tmp.name
    raise FileNotFoundError(
        "credentials.json 파일이 없거나 GOOGLE_SHEETS_CREDS 환경변수가 설정되지 않았습니다."
    )

# === 포트폴리오 시트 탭 이름 ===
SHEET_TAB_NAME = "포트폴리오"  # Google Sheets 탭 이름

# === 리포트 시간대 ===
TIMEZONE = "Asia/Seoul"
