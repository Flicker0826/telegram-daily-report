"""Gemini API를 활용한 지능형 시장/포트폴리오 분석"""
import json
import time
import requests
from typing import Any

import config


GEMINI_BASE = "https://generativelanguage.googleapis.com/v1beta/models/"
GEMINI_MODELS = ["gemini-2.5-flash", "gemini-2.5-flash-lite"]


# ── 투자자 프로필 (진호) ──
INVESTOR_PROFILE = """
## 투자자 프로필
- 월 투자 가능액: 약 200만원
- 목표: 2028년 중순까지 총 자산 9,000만원 ~ 1억원 달성
- 투자 성향: 중위험·중수익, 성장주 + 안정 자산 혼합
- 현재 직장인 (호텔 F&B → 금융권 이직 준비 중)
"""


def build_analysis_prompt(
    market_data: dict,
    portfolio_summary: dict,
    news_text: str,
) -> str:
    """분석용 프롬프트 생성"""

    # ── 글로벌 지수 ──
    indices_text = ""
    for name, d in market_data.get("indices", {}).items():
        sign = "▲" if d.get("change", 0) >= 0 else "▼"
        indices_text += (
            f"  {name}: {d.get('value', 'N/A'):,.2f} "
            f"(전일 {d.get('prev_value', 'N/A'):,.2f} → {sign}{abs(d.get('change', 0)):,.2f}, "
            f"{d.get('change_pct', 0):+.2f}%)\n"
        )

    # ── 환율 ──
    fx_text = ""
    for pair, d in market_data.get("exchange_rates", {}).items():
        sign = "▲" if d.get("change", 0) >= 0 else "▼"
        fx_text += (
            f"  {pair}: {d.get('rate', 'N/A'):,.2f} "
            f"(전일 {d.get('prev_rate', 'N/A'):,.2f} → {sign}{abs(d.get('change', 0)):,.2f}, "
            f"{d.get('change_pct', 0):+.2f}%)\n"
        )

    # ── 금리 ──
    rate_text = ""
    for name, d in market_data.get("interest_rates", {}).items():
        if "change_bp" in d:
            sign = "▲" if d["change_bp"] >= 0 else "▼"
            rate_text += (
                f"  {name}: {d['rate_pct']:.3f}% "
                f"(전일 {d['prev_rate_pct']:.3f}% → {sign}{abs(d['change_bp']):.1f}bp)\n"
            )
        else:
            rate_text += f"  {name}: {d['rate_pct']}% ({d.get('note', '')})\n"

    # ── 포트폴리오 ──
    has_portfolio = bool(portfolio_summary.get("holdings"))
    holdings_text = ""
    for h in portfolio_summary.get("holdings", []):
        daily_sign = "▲" if h.get("daily_change_pct", 0) >= 0 else "▼"
        pnl_sign = "+" if h["pnl"] >= 0 else ""
        holdings_text += (
            f"  {h['name']}({h['ticker']})\n"
            f"    매수가 {h['buy_price']:,.0f} → 현재 {h['current_price']:,.0f} "
            f"(전일대비 {daily_sign}{abs(h.get('daily_change_pct', 0)):.2f}%)\n"
            f"    수량 {h['quantity']}주 | 평가액 {h['current_value']:,.0f}원 | "
            f"수익 {pnl_sign}{h['pnl']:,.0f}원 ({h['pnl_pct']:+.1f}%) | "
            f"비중 {h['weight_pct']:.1f}%\n"
        )

    if has_portfolio:
        portfolio_section = f"""## 내 포트폴리오 현황
총 투자금: {portfolio_summary.get('total_invested', 0):,.0f}원
현재 평가액: {portfolio_summary.get('total_current', 0):,.0f}원
총 수익률: {portfolio_summary.get('total_return_pct', 0):+.2f}%
총 손익: {portfolio_summary.get('total_pnl', 0):+,.0f}원

### 종목별 상세
{holdings_text}"""
    else:
        portfolio_section = "(포트폴리오 데이터 없음 — 시장 분석만 수행)"

    prompt = f"""당신은 전문 금융 어드바이저입니다. 아래 실시간 데이터를 분석하여 한국어로 일일 금융 브리핑을 작성하세요.

{INVESTOR_PROFILE}

## 오늘의 경제 지표

### 글로벌 지수 (전일 대비)
{indices_text}

### 환율 (전일 대비)
{fx_text}

### 금리
{rate_text}

### 섹터별 뉴스
{news_text}

{portfolio_section}

---

## 리포트 작성 지침
텔레그램 메시지로 발송됩니다. 이모지를 활용하고 가독성 좋게 작성하세요.

### 1. 📊 경제 지표 대시보드
- 위 지수, 환율, 금리 데이터를 **수치 그대로** 보여주되 전일 대비 증감(▲▼)을 표시
- 한국은행 기준금리 최신 여부를 확인하고, 다음 금통위 예상 결정 방향 언급
- 미국 FOMC 금리 전망 간략히 언급 (동결/인하/인상 중 시장 컨센서스)
- 주요 환율의 단기 방향성 한줄 코멘트

### 2. 📰 섹터별 뉴스 인사이트
- 5개 섹터(거시경제/금융, 반도체/IT, 에너지/소재, 바이오/헬스케어, 글로벌/지정학) 각각 핵심 1~2줄 요약
- 각 섹터 뉴스가 투자자에게 미치는 영향을 한줄로

### 3. 💰 포트폴리오 성과 분석
- 전체 수익률, 오늘의 평가손익 변동
- 종목별: 현재가, 전일대비 등락, 누적 수익금, 수익률을 표로 간결하게
- 특히 큰 움직임이 있는 종목에 대한 원인 분석

### 4. 🔄 리밸런싱 & 신규 편입 제안
- 현재 포트폴리오의 섹터/시장 편중도 분석
- 투자자 프로필(월 200만원, 2028년 중순 목표 9천만~1억)에 맞는 구체적 비중 조정안
- **신규 편입 추천 종목 2~3개** (종목명, 추천 근거, 제안 비중 포함)
  - 현재 포트폴리오에 없는 섹터 다각화 관점
  - ETF도 포함 가능

### 5. ⚡ Today's Action
- 오늘 주시해야 할 이벤트 (경제 지표 발표, 실적 발표 등)
- 즉시 행동이 필요한 사항이 있다면 구체적으로

전체 분량은 텔레그램 메시지 2개 이내(약 3000~4000자)로 유지하세요.
투자 판단의 최종 책임은 투자자에게 있다는 면책 문구를 마지막에 짧게 포함하세요.
"""
    return prompt


def _call_gemini(model: str, prompt: str) -> tuple[bool, str]:
    """단일 Gemini 모델 호출"""
    url = f"{GEMINI_BASE}{model}:generateContent?key={config.GEMINI_API_KEY}"
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": 0.7, "maxOutputTokens": 4096},
    }
    response = requests.post(url, json=payload, headers={"Content-Type": "application/json"}, timeout=90)
    if response.status_code == 200:
        data = response.json()
        text = data.get("candidates", [{}])[0].get("content", {}).get("parts", [{}])[0].get("text", "")
        return (True, text) if text else (False, "빈 응답")
    return (False, f"HTTP {response.status_code}")


def analyze_with_gemini(
    market_data: dict,
    portfolio_summary: dict,
    news_text: str,
) -> str:
    """Gemini API로 분석 (자동 재시도 + 대체 모델)"""
    if not config.GEMINI_API_KEY:
        print("  ❌ GEMINI_API_KEY가 설정되지 않았습니다!")
        return "⚠️ Gemini API 키가 설정되지 않아 분석을 수행하지 못했습니다."

    prompt = build_analysis_prompt(market_data, portfolio_summary, news_text)
    print(f"  → 프롬프트 {len(prompt)}자 준비 완료")

    for model in GEMINI_MODELS:
        for attempt in range(1, 3):
            try:
                print(f"  → [{model}] 시도 {attempt}/2...")
                success, result = _call_gemini(model, prompt)
                if success:
                    print(f"  ✅ {model} 분석 성공 ({len(result)}자)")
                    return result
                print(f"  ⚠️ {model} 실패: {result}")
                if "429" in result or "503" in result:
                    time.sleep(10 * attempt)
                else:
                    break
            except requests.exceptions.Timeout:
                print(f"  ⚠️ {model} 타임아웃")
                if attempt < 2:
                    time.sleep(5)
            except Exception as e:
                print(f"  ⚠️ {model} 오류: {e}")
                break
        print(f"  → {model} 실패, 다음 모델 시도...")

    return "⚠️ 모든 Gemini 모델이 일시적으로 응답 불가합니다."


def analyze_with_claude(market_data: dict, portfolio_summary: dict, news_text: str) -> str:
    """Claude API 대안 (유료)"""
    claude_api_key = os.environ.get("CLAUDE_API_KEY", "")
    if not claude_api_key:
        return ""
    prompt = build_analysis_prompt(market_data, portfolio_summary, news_text)
    try:
        response = requests.post(
            "https://api.anthropic.com/v1/messages",
            json={"model": "claude-sonnet-4-20250514", "max_tokens": 4096,
                  "messages": [{"role": "user", "content": prompt}]},
            headers={"x-api-key": claude_api_key, "anthropic-version": "2023-06-01",
                     "Content-Type": "application/json"},
            timeout=90,
        )
        response.raise_for_status()
        return response.json()["content"][0]["text"]
    except Exception as e:
        return f"⚠️ Claude API 오류: {e}"
