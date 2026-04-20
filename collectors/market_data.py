"""주가, 환율, 금리, 글로벌 지수 데이터 수집"""
import datetime
import warnings
import os
from typing import Any

os.environ.setdefault("KRX_VERBOSE", "0")
warnings.filterwarnings("ignore", module="pykrx")

from pykrx import stock as krx_stock
import yfinance as yf


def _get_trading_date() -> str:
    today = datetime.date.today()
    offset = max(0, today.weekday() - 4)
    return (today - datetime.timedelta(days=offset)).strftime("%Y%m%d")


def get_krx_stock_price(ticker: str) -> dict[str, Any]:
    """KRX 종목 현재가 + 전일 대비"""
    try:
        end = _get_trading_date()
        start = (datetime.date.today() - datetime.timedelta(days=10)).strftime("%Y%m%d")
        df = krx_stock.get_market_ohlcv(start, end, ticker)
        if df.empty:
            return {"ticker": ticker, "error": "데이터 없음"}
        latest, prev = df.iloc[-1], (df.iloc[-2] if len(df) > 1 else df.iloc[-1])
        close, prev_close = int(latest["종가"]), int(prev["종가"])
        return {
            "ticker": ticker, "close": close, "prev_close": prev_close,
            "change": close - prev_close,
            "change_pct": round(float(latest["등락률"]), 2),
            "volume": int(latest["거래량"]),
        }
    except Exception as e:
        return {"ticker": ticker, "error": str(e)}


def get_us_stock_price(ticker: str) -> dict[str, Any]:
    """미국 주식 현재가 + 전일 대비"""
    try:
        hist = yf.Ticker(ticker).history(period="5d")
        if hist.empty:
            return {"ticker": ticker, "error": "데이터 없음"}
        latest, prev = hist.iloc[-1], (hist.iloc[-2] if len(hist) > 1 else hist.iloc[-1])
        close = round(float(latest["Close"]), 2)
        prev_close = round(float(prev["Close"]), 2)
        return {
            "ticker": ticker, "close": close, "prev_close": prev_close,
            "change": round(close - prev_close, 2),
            "change_pct": round(((close - prev_close) / prev_close) * 100, 2),
            "volume": int(latest["Volume"]), "currency": "USD",
        }
    except Exception as e:
        return {"ticker": ticker, "error": str(e)}


def get_exchange_rates() -> dict[str, Any]:
    """주요 환율 + 전일 대비"""
    pairs = {"USD/KRW": "KRW=X", "JPY/KRW": "JPYKRW=X", "EUR/KRW": "EURKRW=X", "CNY/KRW": "CNYKRW=X"}
    rates = {}
    for name, symbol in pairs.items():
        try:
            hist = yf.Ticker(symbol).history(period="5d")
            if not hist.empty:
                latest, prev = float(hist.iloc[-1]["Close"]), float(hist.iloc[-2]["Close"]) if len(hist) > 1 else float(hist.iloc[-1]["Close"])
                rates[name] = {
                    "rate": round(latest, 2), "prev_rate": round(prev, 2),
                    "change": round(latest - prev, 2),
                    "change_pct": round(((latest - prev) / prev) * 100, 2),
                }
        except Exception:
            rates[name] = {"rate": 0, "change_pct": 0, "error": "조회 실패"}
    return rates


def get_global_indices() -> dict[str, Any]:
    """글로벌 주요 지수 + 전일 대비"""
    indices = {
        "KOSPI": "^KS11", "KOSDAQ": "^KQ11",
        "S&P500": "^GSPC", "NASDAQ": "^IXIC", "다우": "^DJI",
        "닛케이225": "^N225", "항셍": "^HSI", "상해종합": "000001.SS",
    }
    result = {}
    for name, symbol in indices.items():
        try:
            hist = yf.Ticker(symbol).history(period="5d")
            if not hist.empty:
                latest, prev = float(hist.iloc[-1]["Close"]), float(hist.iloc[-2]["Close"]) if len(hist) > 1 else float(hist.iloc[-1]["Close"])
                result[name] = {
                    "value": round(latest, 2), "prev_value": round(prev, 2),
                    "change": round(latest - prev, 2),
                    "change_pct": round(((latest - prev) / prev) * 100, 2),
                }
        except Exception:
            result[name] = {"value": 0, "change_pct": 0, "error": "조회 실패"}
    return result


def get_interest_rates() -> dict[str, Any]:
    """한국/미국 금리 지표"""
    tickers = {
        "미국 10년물 국채": "^TNX",
        "미국 2년물 국채": "^IRX",
        "미국 5년물 국채": "^FVX",
    }
    rates = {}
    for name, symbol in tickers.items():
        try:
            hist = yf.Ticker(symbol).history(period="5d")
            if not hist.empty:
                latest = round(float(hist.iloc[-1]["Close"]), 3)
                prev = round(float(hist.iloc[-2]["Close"]), 3) if len(hist) > 1 else latest
                rates[name] = {
                    "rate_pct": latest, "prev_rate_pct": prev,
                    "change_bp": round((latest - prev) * 100, 1),
                }
        except Exception:
            rates[name] = {"rate_pct": 0, "error": "조회 실패"}

    rates["한국 기준금리(BOK)"] = {
        "rate_pct": 2.75,
        "note": "최신 BOK 발표 기준 — Gemini가 최신 여부 확인",
    }
    return rates


def collect_all_market_data(portfolio_tickers: dict[str, str] | None = None) -> dict:
    """전체 시장 데이터 수집"""
    data = {
        "indices": get_global_indices(),
        "exchange_rates": get_exchange_rates(),
        "interest_rates": get_interest_rates(),
        "portfolio_prices": {},
    }
    if portfolio_tickers:
        for ticker, market in portfolio_tickers.items():
            if market == "KRX":
                data["portfolio_prices"][ticker] = get_krx_stock_price(ticker)
            elif market == "US":
                data["portfolio_prices"][ticker] = get_us_stock_price(ticker)
    return data
