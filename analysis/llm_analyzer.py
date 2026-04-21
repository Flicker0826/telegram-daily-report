"""Gemini API — 분석 코멘트 전용 (데이터 대시보드는 main.py에서 Python이 생성)"""
import json
import time
import requests
from typing import Any

import config

GEMINI_BASE = "https://generativelanguage.googleapis.com/v1beta/models/"
GEMINI_MODELS = ["gemini-2.5-flash", "gemini-2.5-flash-lite"]

INVESTOR_PROFILE = """
- 월 투자 가능액: 약 200만원
- 목표: 2028년 중순까지 총 자산 9,000만원~1억원 달성
- 투자 성향: 중위험·중수익, 성장주 + 안정 자산 혼합
"""


def build_analysis_prompt(
    market_data: dict,
    portfolio_summary: dict,
    news_text: str,
) -> str:
    """분석 코멘트 전용 프롬프트"""

    # 지수 요약 (LLM 참고용)
    idx = market_data.get("indices", {})
    idx_summary = ", ".join(
        f"{k} {d.get('change_pct', 0):+.2f}%" for k, d in idx.items() if not d.get("error")
    )

    # 환율 요약
    fx = market_data.get("exchange_rates", {})
    fx_summary = ", ".join(
        f"{k} {d.get('rate', 0):,.2f}({d.get('change_pct', 0):+.2f}%)" for k, d in fx.items() if not d.get("error")
    )

    # 금리 요약
    rates = market_data.get("interest_rates", {})
    rate_summary = ", ".join(
        f"{k} {d.get('rate_pct', 0)}%" for k, d in rates.items() if not d.get("error")
    )

    # 포트폴리오 요약
    has_portfolio = bool(portfolio_summary.get("holdings"))
    if has_portfolio:
        holdings_summary = "\n".join(
            f"  {h['name']}({h['ticker']}): 수익률 {h['pnl_pct']:+.1f}%, "
            f"오늘 {h.get('daily_change_pct', 0):+.2f}%, 비중 {h['weight_pct']:.1f}%"
            for h in portfolio_summary.get("holdings", [])
        )
        portfolio_text = f"""총 투자금 {portfolio_summary.get('total_invested', 0):,.0f}원
현재 평가액 {portfolio_summary.get('total_current', 0):,.0f}원
총 수익률 {portfolio_summary.get('total_return_pct', 0):+.2f}%

종목별:
{holdings_summary}"""
    else:
        portfolio_text = "(포트폴리오 없음)"

    prompt = f"""당신은 전문 금융 어드바이저입니다.
아래 데이터를 참고하여 **분석 코멘트**만 작성하세요.
(수치 데이터 대시보드는 별도로 이미 만들어져 있으므로, 수치를 반복 나열하지 마세요.)

## 투자자 프로필
{INVESTOR_PROFILE}

## 참고 데이터 (코멘트 작성용)
지수: {idx_summary}
환율: {fx_summary}
금리: {rate_summary}
포트폴리오: {portfolio_text}

## 섹터별 뉴스
{news_text}

---

## 작성할 내용 (텔레그램 메시지, 이모지 활용)

### 🔎 시장 코멘트 (3~4줄)
- 오늘 시장 흐름의 핵심 원인과 배경 분석
- 환율 방향성 한줄 코멘트
- 한국은행 기준금리 현황과 다음 금통위 예상 방향 (동결/인하)
- 미국 FOMC 금리 전망 한줄 (시장 컨센서스 기준)

### 📰 섹터별 뉴스 인사이트
5개 섹터별 각각 핵심 1~2줄:
- 거시경제/금융
- 반도체/IT
- 에너지/소재
- 바이오/헬스케어
- 글로벌/지정학
각 섹터 뉴스가 투자에 미치는 영향 한줄 코멘트 포함

### 📝 포트폴리오 코멘트
- 오늘 가장 주목할 종목 2~3개에 대한 등락 원인 분석
- 전체 포트폴리오 리스크 포인트 (섹터 편중, 비중 집중 등)

### 🔄 리밸런싱 & 신규 편입 제안
- 구체적인 비중 조정안 (예: "삼성전자 35% → 25% 축소")
- **신규 편입 추천 종목 2~3개**: 종목명, 추천 근거, 제안 비중 포함
  - 현재 포트폴리오에 없는 섹터 다각화 관점
  - ETF도 포함 가능 (예: KODEX 200, TIGER 미국S&P500 등)
- 월 200만원 투자 시 어떻게 배분하면 좋을지 구체적 제안

### ⚡ Today's Action
- 오늘 주시할 이벤트 (경제지표 발표, 실적 발표 등)
- 매수/매도 타이밍 관련 조언

마지막에 "※ 본 리포트는 참고용이며 투자 판단의 최종 책임은 투자자에게 있습니다." 한줄 추가.

중요: 전체 분량은 반드시 2000자 이상, 3500자 이하로 작성하세요. 
각 섹션을 빠짐없이 모두 작성해야 합니다. 절대로 축약하거나 생략하지 마세요.
"""
    return prompt


def _call_gemini(model: str, prompt: str) -> tuple[bool, str]:
    url = f"{GEMINI_BASE}{model}:generateContent?key={config.GEMINI_API_KEY}"
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "temperature": 0.7,
            "maxOutputTokens": 16384,  # thinking 토큰 포함이므로 넉넉히
        },
    }
    response = requests.post(url, json=payload, headers={"Content-Type": "application/json"}, timeout=120)
    if response.status_code == 200:
        data = response.json()
        # thinking 모델은 parts가 여러 개일 수 있음 — 마지막 text part가 실제 응답
        parts = data.get("candidates", [{}])[0].get("content", {}).get("parts", [])
        text = ""
        for part in parts:
            if part.get("text"):
                text = part["text"]  # 마지막 text part가 최종 응답
        return (True, text) if text else (False, "빈 응답")
    return (False, f"HTTP {response.status_code}")


def analyze_with_gemini(market_data: dict, portfolio_summary: dict, news_text: str) -> str:
    """Gemini 분석 (자동 재시도 + 대체 모델)"""
    if not config.GEMINI_API_KEY:
        print("  ❌ GEMINI_API_KEY 미설정")
        return "⚠️ Gemini API 키가 설정되지 않아 분석을 수행하지 못했습니다."

    prompt = build_analysis_prompt(market_data, portfolio_summary, news_text)
    print(f"  → 프롬프트 {len(prompt)}자 준비 완료")

    for model in GEMINI_MODELS:
        for attempt in range(1, 3):
            try:
                print(f"  → [{model}] 시도 {attempt}/2...")
                success, result = _call_gemini(model, prompt)
                if success:
                    # 응답이 너무 짧으면 재시도 (thinking에 토큰을 다 쓴 경우)
                    if len(result) < 500:
                        print(f"  ⚠️ {model} 응답 너무 짧음 ({len(result)}자), 재시도...")
                        time.sleep(5)
                        continue
                    print(f"  ✅ {model} 분석 성공 ({len(result)}자)")
                    return result
                print(f"  ⚠️ {model} 실패: {result}")
                if "429" in result or "503" in result:
                    time.sleep(10 * attempt)
                else:
                    break
            except requests.exceptions.Timeout:
                print(f"  ⚠️ {model} 타임아웃")
                if attempt < 2: time.sleep(5)
            except Exception as e:
                print(f"  ⚠️ {model} 오류: {e}")
                break
        print(f"  → {model} 실패, 다음 모델 시도...")

    return "⚠️ 모든 Gemini 모델이 일시적으로 응답 불가합니다."
