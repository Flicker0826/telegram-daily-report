"""주가, 환율, 글로벌 지수 데이터 수집"""
import datetime
import warnings
import os
from typing import Any

# pykrx 로그인 경고 숨기기 (데이터 수집에 영향 없음)
os.environ.setdefault("KRX_VERBOSE", "0")
warnings.filterwarnings("ignore", module="pykrx")

from pykrx import stock as krx_stock
import yfinance as yf


def _get_trading_date() -> str:
    """최근 거래일 반환 (YYYYMMDD)"""
    today = datetime.date.today()
    # 주말이면 금요일로 보정
    offset = max(0, today.weekday() - 4)  # 토=1, 일=2
    trading_date = today - datetime.timedelta(days=offset)
    return trading_date.strftime("%Y%m%d")


def get_krx_stock_price(ticker: str) -> dict[str, Any]:
    """KRX 개별 종목 현재가 조회"""
    date = _get_trading_date()
    try:
        df = krx_stock.get_market_ohlcv(date, date, ticker)
        if df.empty:
            # 하루 전 시도
            prev = (datetime.date.today() - datetime.timedelta(days=1)).strftime("%Y%m%d")
            df = krx_stock.get_market_ohlcv(prev, prev, ticker)
        if df.empty:
            return {"ticker": ticker, "error": "데이터 없음"}
        row = df.iloc[0]
        return {
            "ticker": ticker,
            "close": int(row["종가"]),
            "change_pct": round(float(row["등락률"]), 2),
            "volume": int(row["거래량"]),
            "date": date,
        }
    except Exception as e:
        return {"ticker": ticker, "error": str(e)}


def get_us_stock_price(ticker: str) -> dict[str, Any]:
    """미국 주식 현재가 조회 (yfinance)"""
    try:
        t = yf.Ticker(ticker)
        info = t.fast_info
        hist = t.history(period="2d")
        if hist.empty:
            return {"ticker": ticker, "error": "데이터 없음"}
        latest = hist.iloc[-1]
        prev = hist.iloc[-2] if len(hist) > 1 else hist.iloc[-1]
        change_pct = ((latest["Close"] - prev["Close"]) / prev["Close"]) * 100
        return {
            "ticker": ticker,
            "close": round(float(latest["Close"]), 2),
            "change_pct": round(change_pct, 2),
            "volume": int(latest["Volume"]),
            "currency": "USD",
        }
    except Exception as e:
        return {"ticker": ticker, "error": str(e)}


def get_exchange_rates() -> dict[str, Any]:
    """주요 환율 조회 (yfinance)"""
    pairs = {
        "USD/KRW": "KRW=X",
        "JPY/KRW": "JPYKRW=X",
        "EUR/KRW": "EURKRW=X",
        "CNY/KRW": "CNYKRW=X",
    }
    rates = {}
    for name, symbol in pairs.items():
        try:
            t = yf.Ticker(symbol)
            hist = t.history(period="2d")
            if not hist.empty:
                latest = hist.iloc[-1]["Close"]
                prev = hist.iloc[-2]["Close"] if len(hist) > 1 else latest
                change = ((latest - prev) / prev) * 100
                rates[name] = {
                    "rate": round(float(latest), 2),
                    "change_pct": round(change, 2),
                }
        except Exception:
            rates[name] = {"rate": 0, "change_pct": 0, "error": "조회 실패"}
    return rates


def get_global_indices() -> dict[str, Any]:
    """글로벌 주요 지수 조회"""
    indices = {
        "KOSPI": "^KS11",
        "KOSDAQ": "^KQ11",
        "S&P500": "^GSPC",
        "NASDAQ": "^IXIC",
        "다우": "^DJI",
        "닛케이225": "^N225",
        "항셍": "^HSI",
    }
    result = {}
    for name, symbol in indices.items():
        try:
            t = yf.Ticker(symbol)
            hist = t.history(period="2d")
            if not hist.empty:
                latest = hist.iloc[-1]["Close"]
                prev = hist.iloc[-2]["Close"] if len(hist) > 1 else latest
                change = ((latest - prev) / prev) * 100
                result[name] = {
                    "value": round(float(latest), 2),
                    "change_pct": round(change, 2),
                }
        except Exception:
            result[name] = {"value": 0, "change_pct": 0, "error": "조회 실패"}
    return result


def collect_all_market_data(portfolio_tickers: dict[str, str] | None = None) -> dict:
    """
    전체 시장 데이터 수집
    portfolio_tickers: {"005930": "KRX", "AAPL": "US"} 형태
    """
    data = {
        "indices": get_global_indices(),
        "exchange_rates": get_exchange_rates(),
        "portfolio_prices": {},
    }

    if portfolio_tickers:
        for ticker, market in portfolio_tickers.items():
            if market == "KRX":
                data["portfolio_prices"][ticker] = get_krx_stock_price(ticker)
            elif market == "US":
                data["portfolio_prices"][ticker] = get_us_stock_price(ticker)

    return data
