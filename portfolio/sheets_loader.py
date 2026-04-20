"""Google Sheets에서 포트폴리오 데이터 로드"""
import os
import json
from typing import Any

import gspread
from google.oauth2.service_account import Credentials

import config


SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets.readonly",
    "https://www.googleapis.com/auth/drive.readonly",
]


def _get_client() -> gspread.Client:
    """Google Sheets 클라이언트 생성"""
    creds_path = config.get_google_creds_path()
    credentials = Credentials.from_service_account_file(creds_path, scopes=SCOPES)
    return gspread.authorize(credentials)


def load_portfolio() -> list[dict[str, Any]]:
    """
    Google Sheets에서 포트폴리오 읽기

    시트 형식 (첫 행 = 헤더):
    종목코드 | 종목명 | 매수가 | 수량 | 매수일 | 시장
    005930  | 삼성전자 | 72000 | 10  | 2024-01-15 | KRX
    AAPL    | 애플    | 178.5 | 3   | 2024-02-10 | US
    """
    # ── 사전 체크: 설정 없으면 바로 건너뛰기 ──
    if not config.GOOGLE_SHEET_ID:
        print("  ⏭️ GOOGLE_SHEET_ID 미설정 → 포트폴리오 건너뜀")
        return []

    if not config.GOOGLE_SHEETS_CREDS and not os.path.exists("credentials.json"):
        print("  ⏭️ Google 인증 정보 없음 → 포트폴리오 건너뜀")
        print("     (나중에 설정하면 자동으로 포트폴리오 분석이 추가됩니다)")
        return []

    try:
        client = _get_client()
        sheet = client.open_by_key(config.GOOGLE_SHEET_ID)
        worksheet = sheet.worksheet(config.SHEET_TAB_NAME)
        records = worksheet.get_all_records()

        portfolio = []
        for row in records:
            raw_ticker = str(row.get("종목코드", "")).strip()
            market = str(row.get("시장", "KRX")).strip().upper()

            # KRX 종목코드는 반드시 6자리 → 앞에 0 채우기
            # Google Sheets가 005380을 숫자 5380으로 인식하는 문제 해결
            if market == "KRX" and raw_ticker.isdigit():
                raw_ticker = raw_ticker.zfill(6)

            portfolio.append({
                "ticker": raw_ticker,
                "name": str(row.get("종목명", "")).strip(),
                "buy_price": float(row.get("매수가", 0)),
                "quantity": int(row.get("수량", 0)),
                "buy_date": str(row.get("매수일", "")),
                "market": market,
            })

        return portfolio

    except Exception as e:
        print(f"  ❌ 포트폴리오 로드 실패: {e}")
        return []


def get_ticker_map(portfolio: list[dict]) -> dict[str, str]:
    """
    포트폴리오에서 {ticker: market} 매핑 생성
    시장 데이터 수집에 사용
    """
    return {item["ticker"]: item["market"] for item in portfolio if item["ticker"]}


def calculate_portfolio_summary(
    portfolio: list[dict], current_prices: dict[str, dict]
) -> dict[str, Any]:
    """
    포트폴리오 수익률 계산
    - 가격 조회 실패한 종목도 반드시 포함 (매수가 기준으로 표시)
    """
    holdings = []
    total_invested = 0
    total_current = 0
    failed_tickers = []

    for item in portfolio:
        ticker = item["ticker"]
        price_data = current_prices.get(ticker, {})
        current_price = price_data.get("close", 0)

        # 가격 조회 실패 시 매수가를 fallback으로 사용
        if current_price == 0:
            failed_tickers.append(f"{item['name']}({ticker})")
            current_price = item["buy_price"]  # 매수가로 대체
            price_data = {
                "close": current_price,
                "prev_close": current_price,
                "change_pct": 0,
                "error": "가격 조회 실패 — 매수가 기준 표시",
            }

        invested = item["buy_price"] * item["quantity"]
        current_val = current_price * item["quantity"]
        pnl = current_val - invested
        pnl_pct = ((current_price - item["buy_price"]) / item["buy_price"]) * 100 if item["buy_price"] > 0 else 0

        total_invested += invested
        total_current += current_val

        holdings.append({
            "ticker": ticker,
            "name": item["name"],
            "buy_price": item["buy_price"],
            "current_price": current_price,
            "prev_close": price_data.get("prev_close", current_price),
            "quantity": item["quantity"],
            "invested": invested,
            "current_value": current_val,
            "pnl": round(pnl),
            "pnl_pct": round(pnl_pct, 2),
            "daily_change_pct": price_data.get("change_pct", 0),
            "weight_pct": 0,
            "price_error": price_data.get("error", ""),
        })

    if failed_tickers:
        print(f"  ⚠️ 가격 조회 실패 종목 (매수가로 대체): {', '.join(failed_tickers)}")

    # 비중 계산
    for h in holdings:
        h["weight_pct"] = round((h["current_value"] / total_current) * 100, 1) if total_current > 0 else 0

    total_return_pct = (
        ((total_current - total_invested) / total_invested) * 100
        if total_invested > 0
        else 0
    )

    return {
        "total_invested": round(total_invested),
        "total_current": round(total_current),
        "total_pnl": round(total_current - total_invested),
        "total_return_pct": round(total_return_pct, 2),
        "holdings": sorted(holdings, key=lambda x: x["weight_pct"], reverse=True),
        "failed_count": len(failed_tickers),
    }
