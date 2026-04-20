"""
Daily Financial Report Bot - 메인 실행 파일
매일 실행되어 경제 데이터 수집 → LLM 분석 → 텔레그램 전송
"""
import sys
import os
import traceback
import datetime
import warnings

# pykrx 경고 전역 억제
os.environ.setdefault("KRX_VERBOSE", "0")
warnings.filterwarnings("ignore", module="pykrx")

from collectors.market_data import collect_all_market_data
from collectors.news_collector import fetch_news, format_news_for_prompt
from portfolio.sheets_loader import (
    load_portfolio,
    get_ticker_map,
    calculate_portfolio_summary,
)
from analysis.llm_analyzer import analyze_with_gemini
from messenger.telegram_sender import send_message, send_error_alert


def build_header() -> str:
    """리포트 헤더"""
    now = datetime.datetime.now()
    return (
        f"📈 *일일 금융 브리핑*\n"
        f"📅 {now.strftime('%Y년 %m월 %d일 %A')}\n"
        f"{'─' * 28}\n"
    )


def build_raw_summary(market_data: dict, portfolio_summary: dict) -> str:
    """LLM 분석 실패 시 기본 데이터 리포트"""
    lines = [build_header()]

    # 지수
    lines.append("📊 *글로벌 지수*")
    for name, d in market_data.get("indices", {}).items():
        sign = "🔺" if d.get("change_pct", 0) >= 0 else "🔻"
        lines.append(f"  {name}: {d.get('value', 'N/A')} {sign}{abs(d.get('change_pct', 0)):.2f}%")

    # 환율
    lines.append("\n💱 *환율*")
    for pair, d in market_data.get("exchange_rates", {}).items():
        lines.append(f"  {pair}: {d.get('rate', 'N/A')}")

    # 포트폴리오
    if portfolio_summary.get("holdings"):
        lines.append(f"\n💰 *포트폴리오* (수익률: {portfolio_summary['total_return_pct']:+.2f}%)")
        for h in portfolio_summary["holdings"]:
            lines.append(f"  {h['name']}: {h['pnl_pct']:+.1f}% ({h['weight_pct']:.0f}%)")

    return "\n".join(lines)


def run():
    """메인 파이프라인 실행"""
    print("=" * 50)
    print(f"[{datetime.datetime.now()}] Daily Report 시작")
    print("=" * 50)

    try:
        # ── Step 1: 포트폴리오 로드 ──
        print("\n[1/4] 포트폴리오 로드 중...")
        portfolio = load_portfolio()
        if not portfolio:
            print("  ⚠️ 포트폴리오 데이터 없음 (시장 데이터만 전송)")
        else:
            print(f"  ✅ {len(portfolio)}개 종목 로드 완료")

        ticker_map = get_ticker_map(portfolio)

        # ── Step 2: 시장 데이터 수집 ──
        print("\n[2/4] 시장 데이터 수집 중...")
        market_data = collect_all_market_data(ticker_map)
        print(f"  ✅ 지수 {len(market_data.get('indices', {}))}개, "
              f"환율 {len(market_data.get('exchange_rates', {}))}개, "
              f"종목가격 {len(market_data.get('portfolio_prices', {}))}개 수집")

        # 포트폴리오 수익률 계산
        portfolio_summary = calculate_portfolio_summary(
            portfolio, market_data.get("portfolio_prices", {})
        )

        # ── Step 3: 뉴스 수집 ──
        print("\n[3/4] 뉴스 수집 중...")
        articles = fetch_news(max_items=5)
        news_text = format_news_for_prompt(articles)
        print(f"  ✅ 뉴스 {len(articles)}건 수집")

        # ── Step 4: LLM 분석 ──
        print("\n[4/4] Gemini 분석 중...")
        analysis = analyze_with_gemini(market_data, portfolio_summary, news_text)

        if analysis.startswith("⚠️"):
            print(f"  ⚠️ LLM 분석 실패, 기본 리포트로 대체")
            report = build_raw_summary(market_data, portfolio_summary)
        else:
            report = build_header() + analysis
            print(f"  ✅ 분석 완료 ({len(analysis)}자)")

        # ── Step 5: 텔레그램 전송 ──
        print("\n[전송] 텔레그램 메시지 전송 중...")
        success = send_message(report)

        if success:
            print("  ✅ 전송 완료!")
        else:
            print("  ❌ 전송 실패")

        return success

    except Exception as e:
        error_msg = f"{type(e).__name__}: {e}\n{traceback.format_exc()}"
        print(f"\n❌ 오류 발생:\n{error_msg}")

        # 에러도 텔레그램으로 알림
        try:
            send_error_alert(error_msg)
        except Exception:
            pass

        return False


if __name__ == "__main__":
    success = run()
    sys.exit(0 if success else 1)
