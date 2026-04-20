"""
Daily Financial Report Bot - 메인 실행 파일
데이터 대시보드는 Python이 정확한 수치로 생성,
분석/코멘트는 Gemini가 담당
"""
import sys
import os
import traceback
import datetime
import warnings

os.environ.setdefault("KRX_VERBOSE", "0")
warnings.filterwarnings("ignore", module="pykrx")

from collectors.market_data import collect_all_market_data
from collectors.news_collector import fetch_news, format_news_for_prompt
from portfolio.sheets_loader import (
    load_portfolio, get_ticker_map, calculate_portfolio_summary,
)
from analysis.llm_analyzer import analyze_with_gemini
from messenger.telegram_sender import send_message, send_error_alert


def build_header() -> str:
    now = datetime.datetime.now()
    return (
        f"📈 *일일 금융 브리핑*\n"
        f"📅 {now.strftime('%Y년 %m월 %d일 %A')}\n"
        f"{'─' * 28}\n"
    )


def build_indices_section(indices: dict) -> str:
    """글로벌 지수 — Python이 정확한 수치로 생성"""
    lines = ["📊 *글로벌 지수*"]
    for name, d in indices.items():
        if d.get("error"):
            continue
        sign = "🔺" if d.get("change", 0) >= 0 else "🔻"
        lines.append(
            f"  {name}: {d['value']:,.2f}  "
            f"{sign}{abs(d.get('change', 0)):,.2f} ({d.get('change_pct', 0):+.2f}%)\n"
            f"    전일 {d.get('prev_value', 0):,.2f}"
        )
    return "\n".join(lines)


def build_fx_section(rates: dict) -> str:
    """환율 — Python이 정확한 수치로 생성"""
    lines = ["\n💱 *환율*"]
    for pair, d in rates.items():
        if d.get("error"):
            continue
        sign = "🔺" if d.get("change", 0) >= 0 else "🔻"
        lines.append(
            f"  {pair}: {d['rate']:,.2f}  "
            f"{sign}{abs(d.get('change', 0)):,.2f} ({d.get('change_pct', 0):+.2f}%)\n"
            f"    전일 {d.get('prev_rate', 0):,.2f}"
        )
    return "\n".join(lines)


def build_rates_section(interest_rates: dict) -> str:
    """금리 — Python이 정확한 수치로 생성"""
    lines = ["\n📉 *금리*"]
    for name, d in interest_rates.items():
        if d.get("error"):
            continue
        if "change_bp" in d:
            sign = "▲" if d["change_bp"] >= 0 else "▼"
            lines.append(
                f"  {name}: {d['rate_pct']:.3f}%  "
                f"{sign}{abs(d['change_bp']):.1f}bp\n"
                f"    전일 {d['prev_rate_pct']:.3f}%"
            )
        else:
            lines.append(f"  {name}: {d['rate_pct']}%  ({d.get('note', '')})")
    return "\n".join(lines)


def build_portfolio_section(portfolio_summary: dict) -> str:
    """포트폴리오 — Python이 정확한 수치로 생성"""
    if not portfolio_summary.get("holdings"):
        return ""

    pnl_sign = "+" if portfolio_summary["total_pnl"] >= 0 else ""
    failed = portfolio_summary.get("failed_count", 0)
    failed_note = f"  ⚠️ {failed}개 종목 가격 조회 실패 (매수가 기준)\n" if failed else ""

    lines = [
        f"\n💰 *포트폴리오 현황* ({len(portfolio_summary['holdings'])}종목)",
        f"  평가액: {portfolio_summary['total_current']:,.0f}원 "
        f"(투자금 {portfolio_summary['total_invested']:,.0f}원)",
        f"  총 수익: {pnl_sign}{portfolio_summary['total_pnl']:,.0f}원 "
        f"({portfolio_summary['total_return_pct']:+.2f}%)",
        failed_note,
        f"  *종목별 상세*",
    ]

    for h in portfolio_summary["holdings"]:
        error_tag = " ⚠️" if h.get("price_error") else ""
        daily_icon = "🔺" if h.get("daily_change_pct", 0) >= 0 else "🔻"
        pnl_s = "+" if h["pnl"] >= 0 else ""
        lines.append(
            f"  ▸ {h['name']} ({h['ticker']}){error_tag}\n"
            f"    전일 {h.get('prev_close', '-'):,} → 현재 {h['current_price']:,}  "
            f"{daily_icon}{abs(h.get('daily_change_pct', 0)):.2f}%\n"
            f"    매수가 {h['buy_price']:,} × {h['quantity']}주\n"
            f"    수익 {pnl_s}{h['pnl']:,}원 ({h['pnl_pct']:+.1f}%) | "
            f"비중 {h['weight_pct']:.1f}%"
        )

    return "\n".join(lines)


def build_raw_summary(market_data: dict, portfolio_summary: dict) -> str:
    """LLM 분석 실패 시 데이터만 전송"""
    parts = [build_header()]
    parts.append(build_indices_section(market_data.get("indices", {})))
    parts.append(build_fx_section(market_data.get("exchange_rates", {})))
    parts.append(build_rates_section(market_data.get("interest_rates", {})))
    parts.append(build_portfolio_section(portfolio_summary))
    return "\n".join(parts)


def run():
    """메인 파이프라인"""
    print("=" * 50)
    print(f"[{datetime.datetime.now()}] Daily Report 시작")
    print("=" * 50)

    try:
        # ── Step 1: 포트폴리오 ──
        print("\n[1/4] 포트폴리오 로드 중...")
        portfolio = load_portfolio()
        if not portfolio:
            print("  ⚠️ 포트폴리오 데이터 없음 (시장 데이터만 전송)")
        else:
            print(f"  ✅ {len(portfolio)}개 종목 로드 완료")

        ticker_map = get_ticker_map(portfolio)

        # ── Step 2: 시장 데이터 ──
        print("\n[2/4] 시장 데이터 수집 중...")
        market_data = collect_all_market_data(ticker_map)
        print(f"  ✅ 지수 {len(market_data.get('indices', {}))}개, "
              f"환율 {len(market_data.get('exchange_rates', {}))}개, "
              f"금리 {len(market_data.get('interest_rates', {}))}개, "
              f"종목가격 {len(market_data.get('portfolio_prices', {}))}개 수집")

        # 포트폴리오 수익률 계산
        portfolio_summary = calculate_portfolio_summary(
            portfolio, market_data.get("portfolio_prices", {})
        )

        # ── Step 3: 뉴스 ──
        print("\n[3/4] 섹터별 뉴스 수집 중...")
        sector_news = fetch_news(max_per_sector=3)
        news_text = format_news_for_prompt(sector_news)
        total_articles = sum(len(v) for v in sector_news.values())
        print(f"  ✅ {len(sector_news)}개 섹터, 총 {total_articles}건 수집")

        # ── Step 4: 메시지 조립 ──
        # Part A: 데이터 대시보드 (Python이 정확한 수치로 생성)
        dashboard = build_header()
        dashboard += build_indices_section(market_data.get("indices", {}))
        dashboard += build_fx_section(market_data.get("exchange_rates", {}))
        dashboard += build_rates_section(market_data.get("interest_rates", {}))
        dashboard += build_portfolio_section(portfolio_summary)

        # Part B: AI 분석 (Gemini가 코멘트/인사이트 생성)
        print("\n[4/4] Gemini 분석 중...")
        analysis = analyze_with_gemini(market_data, portfolio_summary, news_text)

        if analysis.startswith("⚠️"):
            print(f"  ⚠️ LLM 분석 실패, 데이터만 전송")
            report = dashboard
        else:
            report = dashboard + "\n\n" + "─" * 28 + "\n\n" + analysis
            print(f"  ✅ 분석 완료 ({len(analysis)}자)")

        # ── Step 5: 전송 ──
        print("\n[전송] 텔레그램 메시지 전송 중...")
        success = send_message(report)
        print("  ✅ 전송 완료!" if success else "  ❌ 전송 실패")
        return success

    except Exception as e:
        error_msg = f"{type(e).__name__}: {e}\n{traceback.format_exc()}"
        print(f"\n❌ 오류 발생:\n{error_msg}")
        try:
            send_error_alert(error_msg)
        except Exception:
            pass
        return False


if __name__ == "__main__":
    sys.exit(0 if run() else 1)
