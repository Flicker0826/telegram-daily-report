"""Gemini API를 활용한 지능형 시장/포트폴리오 분석"""
import json
import time
import requests
from typing import Any

import config


GEMINI_BASE = "https://generativelanguage.googleapis.com/v1beta/models/"

# 우선순위 순서: 2.5 Flash → 2.5 Flash-Lite (대체)
GEMINI_MODELS = [
    "gemini-2.5-flash",
    "gemini-2.5-flash-lite",
]


def build_analysis_prompt(
    market_data: dict,
    portfolio_summary: dict,
    news_text: str,
) -> str:
    """분석용 프롬프트 생성"""

    # 글로벌 지수 포맷
    indices_text = ""
    for name, data in market_data.get("indices", {}).items():
        sign = "▲" if data.get("change_pct", 0) >= 0 else "▼"
        indices_text += f"  {name}: {data.get('value', 'N/A')} ({sign}{abs(data.get('change_pct', 0)):.2f}%)\n"

    # 환율 포맷
    fx_text = ""
    for pair, data in market_data.get("exchange_rates", {}).items():
        sign = "▲" if data.get("change_pct", 0) >= 0 else "▼"
        fx_text += f"  {pair}: {data.get('rate', 'N/A')} ({sign}{abs(data.get('change_pct', 0)):.2f}%)\n"

    # 포트폴리오 포맷
    holdings_text = ""
    has_portfolio = bool(portfolio_summary.get("holdings"))
    for h in portfolio_summary.get("holdings", []):
        sign = "+" if h["pnl_pct"] >= 0 else ""
        holdings_text += (
            f"  {h['name']}({h['ticker']}): "
            f"매수 {h['buy_price']:,.0f} → 현재 {h['current_price']:,.0f} "
            f"({sign}{h['pnl_pct']:.1f}%) | 비중 {h['weight_pct']:.1f}% | "
            f"오늘 {h['daily_change_pct']:+.2f}%\n"
        )

    # 포트폴리오 유무에 따라 프롬프트 분기
    if has_portfolio:
        portfolio_section = f"""## 내 포트폴리오 현황
총 투자금: {portfolio_summary.get('total_invested', 0):,.0f}원
현재 평가액: {portfolio_summary.get('total_current', 0):,.0f}원
총 수익률: {portfolio_summary.get('total_return_pct', 0):+.2f}%
총 손익: {portfolio_summary.get('total_pnl', 0):+,.0f}원

### 종목별 상세
{holdings_text}"""
        analysis_sections = """
1. **📊 시장 요약** (3~4줄)
   - 글로벌/국내 시장 흐름 핵심 요약
   - 환율 동향과 영향

2. **📰 뉴스 인사이트** (3~4줄)
   - 오늘 뉴스 중 내 포트폴리오에 영향을 줄 수 있는 핵심 이슈
   - 섹터별 영향 분석

3. **💰 포트폴리오 분석**
   - 전체 수익률 및 오늘의 변동
   - 종목별 한줄 코멘트 (상승/하락 원인)
   - 집중 비중 리스크가 있다면 언급

4. **🔄 리밸런싱 제안**
   - 현재 포트폴리오의 섹터/시장 편중 분석
   - 구체적인 비중 조정 제안 (예: "삼성전자 비중 40% → 30%로 축소 검토")
   - 신규 편입 고려 종목 (있다면)

5. **⚡ 오늘의 액션 포인트** (1~2줄)
   - 오늘 해야 할 것 / 지켜봐야 할 것"""
    else:
        portfolio_section = "(포트폴리오 데이터 없음 — 시장 분석만 수행)"
        analysis_sections = """
1. **📊 시장 요약** (3~4줄)
   - 글로벌/국내 시장 흐름 핵심 요약
   - 환율 동향과 영향

2. **📰 뉴스 인사이트** (3~4줄)
   - 오늘 뉴스 중 투자자에게 중요한 핵심 이슈
   - 섹터별 영향 분석

3. **🔍 주목할 섹터 & 종목**
   - 오늘 시장 흐름에서 주목할 만한 섹터
   - 관심 가질 만한 종목 언급

4. **⚡ 오늘의 액션 포인트** (1~2줄)
   - 투자자가 주시해야 할 이벤트/지표"""

    prompt = f"""당신은 개인 금융 어드바이저입니다. 아래 데이터를 분석하여 한국어로 일일 금융 브리핑을 작성하세요.

## 오늘의 시장 데이터

### 글로벌 지수
{indices_text}

### 환율
{fx_text}

### 주요 뉴스
{news_text}

{portfolio_section}

---

## 요청사항
아래 구조로 분석 리포트를 작성하세요. 텔레그램 메시지로 발송되므로 이모지를 활용하고 간결하게 작성하세요.
{analysis_sections}

전체 분량은 텔레그램 메시지 1개에 들어갈 수 있게 적당히 간결하게 유지하세요.
"""
    return prompt


def _call_gemini(model: str, prompt: str) -> tuple[bool, str]:
    """단일 Gemini 모델 호출. (성공여부, 응답텍스트) 반환"""
    url = f"{GEMINI_BASE}{model}:generateContent?key={config.GEMINI_API_KEY}"
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "temperature": 0.7,
            "maxOutputTokens": 2048,
        },
    }

    response = requests.post(
        url,
        json=payload,
        headers={"Content-Type": "application/json"},
        timeout=60,
    )

    if response.status_code == 200:
        data = response.json()
        text = (
            data.get("candidates", [{}])[0]
            .get("content", {})
            .get("parts", [{}])[0]
            .get("text", "")
        )
        return (True, text) if text else (False, "빈 응답")

    return (False, f"HTTP {response.status_code}")


def analyze_with_gemini(
    market_data: dict,
    portfolio_summary: dict,
    news_text: str,
) -> str:
    """Gemini API로 분석 실행 (자동 재시도 + 대체 모델)"""

    # API 키 확인
    if not config.GEMINI_API_KEY:
        print("  ❌ GEMINI_API_KEY가 설정되지 않았습니다!")
        print("  → .env 파일에 GEMINI_API_KEY=AIzaSy-xxxxx 형태로 입력")
        print("  → 키 발급: https://aistudio.google.com/apikey")
        return "⚠️ Gemini API 키가 설정되지 않아 분석을 수행하지 못했습니다."

    prompt = build_analysis_prompt(market_data, portfolio_summary, news_text)
    print(f"  → 프롬프트 {len(prompt)}자 준비 완료")

    # 각 모델에 대해 최대 2회씩 재시도
    for model in GEMINI_MODELS:
        for attempt in range(1, 3):
            try:
                print(f"  → [{model}] 시도 {attempt}/2...")
                success, result = _call_gemini(model, prompt)

                if success:
                    print(f"  ✅ {model} 분석 성공 ({len(result)}자)")
                    return result

                print(f"  ⚠️ {model} 실패: {result}")

                # 429/503은 대기 후 재시도, 그 외는 다음 모델로
                if "429" in result or "503" in result:
                    wait = 10 * attempt
                    print(f"  ⏳ {wait}초 대기 후 재시도...")
                    time.sleep(wait)
                else:
                    break  # 400, 403 등은 재시도 의미 없음

            except requests.exceptions.Timeout:
                print(f"  ⚠️ {model} 타임아웃")
                if attempt < 2:
                    time.sleep(5)
            except Exception as e:
                print(f"  ⚠️ {model} 오류: {e}")
                break

        print(f"  → {model} 실패, 다음 모델 시도...")

    return "⚠️ 모든 Gemini 모델이 일시적으로 응답 불가합니다. 잠시 후 다시 시도하세요."


def analyze_with_claude(
    market_data: dict,
    portfolio_summary: dict,
    news_text: str,
) -> str:
    """
    Claude API로 분석 (대안, API 키 필요)
    Gemini가 안 될 때 fallback으로 사용
    """
    claude_api_key = config.__dict__.get("CLAUDE_API_KEY", "")
    if not claude_api_key:
        return ""

    prompt = build_analysis_prompt(market_data, portfolio_summary, news_text)

    try:
        response = requests.post(
            "https://api.anthropic.com/v1/messages",
            json={
                "model": "claude-sonnet-4-20250514",
                "max_tokens": 2048,
                "messages": [{"role": "user", "content": prompt}],
            },
            headers={
                "x-api-key": claude_api_key,
                "anthropic-version": "2023-06-01",
                "Content-Type": "application/json",
            },
            timeout=60,
        )
        response.raise_for_status()
        data = response.json()
        return data["content"][0]["text"]
    except Exception as e:
        return f"⚠️ Claude API 오류: {e}"
