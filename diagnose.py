"""
🔍 진단 스크립트 — 각 모듈을 개별 테스트하여 어디서 문제가 생기는지 확인
사용법: python diagnose.py
"""
import os
import sys


def load_env():
    env_path = os.path.join(os.path.dirname(__file__), ".env")
    if os.path.exists(env_path):
        with open(env_path) as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                if "=" in line:
                    key, value = line.split("=", 1)
                    os.environ[key.strip()] = value.strip()
        print("✅ .env 파일 로드 완료\n")
    else:
        print("⚠️ .env 파일 없음 — 환경변수가 이미 설정되어 있어야 합니다\n")


def check_env_vars():
    """환경변수 설정 확인"""
    print("=" * 50)
    print("1️⃣  환경변수 확인")
    print("=" * 50)

    vars_to_check = {
        "TELEGRAM_BOT_TOKEN": "텔레그램 봇 토큰",
        "TELEGRAM_CHAT_ID": "텔레그램 Chat ID",
        "GEMINI_API_KEY": "Gemini API 키",
        "GOOGLE_SHEET_ID": "Google Sheets ID",
    }

    all_ok = True
    for var, desc in vars_to_check.items():
        val = os.getenv(var, "")
        if val:
            # 값의 앞뒤 일부만 보여주기 (보안)
            masked = val[:6] + "..." + val[-4:] if len(val) > 12 else val[:4] + "..."
            print(f"  ✅ {desc} ({var}): {masked}")
        else:
            print(f"  ❌ {desc} ({var}): 설정 안 됨!")
            all_ok = False

    # credentials.json 확인
    creds_env = os.getenv("GOOGLE_SHEETS_CREDS", "")
    creds_file = os.path.exists("credentials.json")
    if creds_file:
        print(f"  ✅ credentials.json: 파일 존재")
    elif creds_env:
        print(f"  ✅ GOOGLE_SHEETS_CREDS: 환경변수로 설정됨")
    else:
        print(f"  ⚠️ Google Sheets 인증: credentials.json 없음 & 환경변수 없음")
        print(f"     → 포트폴리오 기능을 쓰려면 Google Cloud 서비스 계정 설정 필요")
        print(f"     → 지금은 건너뛰고 시장 데이터만 테스트 가능")

    print()
    return all_ok


def test_market_data():
    """시장 데이터 수집 테스트"""
    print("=" * 50)
    print("2️⃣  시장 데이터 수집 테스트")
    print("=" * 50)

    try:
        import yfinance as yf

        # KOSPI 테스트
        t = yf.Ticker("^KS11")
        hist = t.history(period="2d")
        if not hist.empty:
            val = round(float(hist.iloc[-1]["Close"]), 2)
            print(f"  ✅ KOSPI: {val}")
        else:
            print(f"  ⚠️ KOSPI: 데이터 없음 (주말/공휴일일 수 있음)")

        # 환율 테스트
        t2 = yf.Ticker("KRW=X")
        hist2 = t2.history(period="2d")
        if not hist2.empty:
            rate = round(float(hist2.iloc[-1]["Close"]), 2)
            print(f"  ✅ USD/KRW: {rate}")

        # S&P 500
        t3 = yf.Ticker("^GSPC")
        hist3 = t3.history(period="2d")
        if not hist3.empty:
            val3 = round(float(hist3.iloc[-1]["Close"]), 2)
            print(f"  ✅ S&P 500: {val3}")

        print(f"  ✅ yfinance 정상 작동")

    except Exception as e:
        print(f"  ❌ 시장 데이터 오류: {e}")
    print()


def test_pykrx():
    """pykrx 테스트"""
    print("=" * 50)
    print("3️⃣  pykrx (KRX 주식) 테스트")
    print("=" * 50)

    try:
        import warnings
        warnings.filterwarnings("ignore")  # pykrx 경고 숨기기

        from pykrx import stock as krx_stock
        import datetime

        today = datetime.date.today()
        # 최근 5일 중 거래일 찾기
        for i in range(5):
            date = (today - datetime.timedelta(days=i)).strftime("%Y%m%d")
            df = krx_stock.get_market_ohlcv(date, date, "005930")
            if not df.empty:
                price = int(df.iloc[0]["종가"])
                print(f"  ✅ 삼성전자(005930): {price:,}원 (날짜: {date})")
                break
        else:
            print(f"  ⚠️ 삼성전자: 최근 5일 데이터 없음")

        print(f"  💡 KRX 로그인 경고는 무시해도 됩니다 (데이터 수집에 영향 없음)")

    except Exception as e:
        print(f"  ❌ pykrx 오류: {e}")
    print()


def test_news():
    """뉴스 RSS 테스트"""
    print("=" * 50)
    print("4️⃣  뉴스 수집 테스트")
    print("=" * 50)

    try:
        import feedparser
        feed = feedparser.parse(
            "https://news.google.com/rss/search?q=한국+경제&hl=ko&gl=KR&ceid=KR:ko"
        )
        count = len(feed.entries)
        if count > 0:
            print(f"  ✅ 뉴스 {count}건 수집")
            print(f"  📰 최신: {feed.entries[0].get('title', 'N/A')}")
        else:
            print(f"  ⚠️ 뉴스 0건")
    except Exception as e:
        print(f"  ❌ 뉴스 수집 오류: {e}")
    print()


def test_gemini():
    """Gemini API 테스트"""
    print("=" * 50)
    print("5️⃣  Gemini API 테스트")
    print("=" * 50)

    api_key = os.getenv("GEMINI_API_KEY", "")
    if not api_key:
        print("  ❌ GEMINI_API_KEY가 설정되지 않았습니다")
        print("  → .env 파일에 GEMINI_API_KEY=AIzaSy-xxxxx 형태로 입력하세요")
        print("  → 키 발급: https://aistudio.google.com/apikey")
        print()
        return

    import requests

    # 간단한 테스트 프롬프트
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={api_key}"

    payload = {
        "contents": [{"parts": [{"text": "한국어로 '안녕하세요, 테스트 성공입니다'라고 답해주세요. 딱 한 문장만."}]}],
        "generationConfig": {"maxOutputTokens": 100},
    }

    try:
        resp = requests.post(url, json=payload, timeout=30)
        print(f"  HTTP 상태코드: {resp.status_code}")

        if resp.status_code == 200:
            data = resp.json()
            text = (
                data.get("candidates", [{}])[0]
                .get("content", {})
                .get("parts", [{}])[0]
                .get("text", "")
            )
            print(f"  ✅ Gemini 응답: {text.strip()}")
        elif resp.status_code == 400:
            print(f"  ❌ 잘못된 요청: {resp.text[:300]}")
            print(f"  → API 키 형식이 올바른지 확인하세요")
        elif resp.status_code == 403:
            print(f"  ❌ API 키 권한 없음: {resp.text[:300]}")
            print(f"  → https://aistudio.google.com/apikey 에서 키를 재발급하세요")
        elif resp.status_code == 429:
            print(f"  ⚠️ 요청 한도 초과 (잠시 후 다시 시도)")
        else:
            print(f"  ❌ 에러: {resp.text[:500]}")

    except requests.exceptions.ConnectionError:
        print(f"  ❌ 네트워크 연결 실패 — 인터넷 연결을 확인하세요")
    except Exception as e:
        print(f"  ❌ 오류: {e}")
    print()


def test_telegram():
    """텔레그램 전송 테스트"""
    print("=" * 50)
    print("6️⃣  텔레그램 전송 테스트")
    print("=" * 50)

    token = os.getenv("TELEGRAM_BOT_TOKEN", "")
    chat_id = os.getenv("TELEGRAM_CHAT_ID", "")

    if not token:
        print("  ❌ TELEGRAM_BOT_TOKEN이 설정되지 않았습니다")
        print()
        return
    if not chat_id:
        print("  ❌ TELEGRAM_CHAT_ID가 설정되지 않았습니다")
        print()
        return

    import requests

    test_msg = "🔍 진단 테스트 메시지\n\n이 메시지가 보이면 텔레그램 연결 성공!"
    try:
        resp = requests.post(
            f"https://api.telegram.org/bot{token}/sendMessage",
            json={"chat_id": chat_id, "text": test_msg},
            timeout=15,
        )
        if resp.status_code == 200:
            print(f"  ✅ 텔레그램 전송 성공! 앱에서 확인하세요")
        else:
            error = resp.json().get("description", resp.text)
            print(f"  ❌ 전송 실패: {error}")
            if "chat not found" in str(error).lower():
                print(f"  → Chat ID가 잘못되었거나, 봇에게 먼저 메시지를 보내야 합니다")
            elif "unauthorized" in str(error).lower():
                print(f"  → Bot Token이 잘못되었습니다")
    except Exception as e:
        print(f"  ❌ 오류: {e}")
    print()


def test_sheets():
    """Google Sheets 연결 테스트"""
    print("=" * 50)
    print("7️⃣  Google Sheets 연결 테스트")
    print("=" * 50)

    sheet_id = os.getenv("GOOGLE_SHEET_ID", "")
    creds_env = os.getenv("GOOGLE_SHEETS_CREDS", "")
    creds_file = os.path.exists("credentials.json")

    if not sheet_id:
        print("  ⚠️ GOOGLE_SHEET_ID가 설정되지 않았습니다")
        print("  → 포트폴리오 기능 없이도 시장 리포트는 정상 작동합니다")
        print("  → 나중에 설정하면 포트폴리오 분석이 추가됩니다")
        print()
        return

    if not creds_file and not creds_env:
        print("  ⚠️ Google 인증 정보가 없습니다")
        print("  → credentials.json 파일을 프로젝트 폴더에 넣거나")
        print("  → GOOGLE_SHEETS_CREDS 환경변수를 설정하세요")
        print()
        return

    try:
        import gspread
        from google.oauth2.service_account import Credentials

        creds_path = "credentials.json"
        if not os.path.exists(creds_path) and creds_env:
            import tempfile
            tmp = tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False)
            tmp.write(creds_env)
            tmp.close()
            creds_path = tmp.name

        scopes = [
            "https://www.googleapis.com/auth/spreadsheets.readonly",
            "https://www.googleapis.com/auth/drive.readonly",
        ]
        credentials = Credentials.from_service_account_file(creds_path, scopes=scopes)
        client = gspread.authorize(credentials)
        sheet = client.open_by_key(sheet_id)
        worksheet = sheet.worksheet("포트폴리오")
        records = worksheet.get_all_records()
        print(f"  ✅ Google Sheets 연결 성공! ({len(records)}개 종목)")
        for r in records[:3]:
            print(f"     {r.get('종목명', '?')} ({r.get('종목코드', '?')})")
        if len(records) > 3:
            print(f"     ... 외 {len(records) - 3}개")
    except Exception as e:
        error_str = str(e)
        print(f"  ❌ Google Sheets 오류: {e}")
        if "not found" in error_str.lower():
            print(f"  → 시트 ID가 잘못되었거나, 서비스 계정에 공유가 안 되어 있습니다")
        elif "포트폴리오" in error_str:
            print(f"  → 시트 하단 탭 이름이 '포트폴리오'인지 확인하세요")
    print()


def print_summary():
    print("=" * 50)
    print("📋 요약 & 다음 단계")
    print("=" * 50)
    print("""
  지금 당장 해결해야 하는 것:
  ──────────────────────────
  1. GEMINI_API_KEY가 .env에 있는지 확인
     → 없으면: https://aistudio.google.com/apikey 에서 발급

  나중에 해도 되는 것 (선택):
  ──────────────────────────
  2. Google Sheets 포트폴리오 연동
     → 없어도 시장 요약 + 뉴스 리포트는 정상 작동
     → 연동하면 내 종목 수익률 분석 + 리밸런싱 조언 추가

  KRX 로그인 경고:
  ──────────────────────────
  → 무시해도 됩니다 (데이터 수집에 영향 없음)
""")


if __name__ == "__main__":
    load_env()
    check_env_vars()
    test_market_data()
    test_pykrx()
    test_news()
    test_gemini()
    test_telegram()
    test_sheets()
    print_summary()
