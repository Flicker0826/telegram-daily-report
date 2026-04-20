"""5개 섹터별 경제 뉴스 RSS 수집"""
import re
import feedparser
from typing import Any


# 5개 섹터별 뉴스 피드
SECTOR_FEEDS = {
    "거시경제/금융": [
        "https://news.google.com/rss/search?q=한국+기준금리+경제+환율&hl=ko&gl=KR&ceid=KR:ko",
        "https://www.mk.co.kr/rss/30100041/",
    ],
    "반도체/IT": [
        "https://news.google.com/rss/search?q=삼성전자+SK하이닉스+반도체+AI&hl=ko&gl=KR&ceid=KR:ko",
    ],
    "에너지/소재": [
        "https://news.google.com/rss/search?q=유가+원자재+2차전지+에너지&hl=ko&gl=KR&ceid=KR:ko",
    ],
    "바이오/헬스케어": [
        "https://news.google.com/rss/search?q=바이오+제약+헬스케어+임상&hl=ko&gl=KR&ceid=KR:ko",
    ],
    "글로벌/지정학": [
        "https://news.google.com/rss/search?q=미중+관세+무역+지정학+글로벌&hl=ko&gl=KR&ceid=KR:ko",
    ],
}


def fetch_news(max_per_sector: int = 3) -> dict[str, list[dict[str, Any]]]:
    """
    섹터별 뉴스 수집
    Returns: {"섹터명": [{"title": ..., "summary": ...}, ...]}
    """
    result = {}

    for sector, urls in SECTOR_FEEDS.items():
        articles = []
        for url in urls:
            try:
                feed = feedparser.parse(url)
                for entry in feed.entries[:max_per_sector]:
                    title = entry.get("title", "")
                    if title and title not in [a["title"] for a in articles]:
                        articles.append({
                            "title": title,
                            "link": entry.get("link", ""),
                            "published": entry.get("published", ""),
                            "summary": _clean_summary(entry.get("summary", "")),
                        })
            except Exception:
                continue

        result[sector] = articles[:max_per_sector]

    return result


def _clean_summary(text: str) -> str:
    clean = re.sub(r"<[^>]+>", "", text).strip()
    return clean[:150] + "..." if len(clean) > 150 else clean


def format_news_for_prompt(sector_news: dict[str, list[dict]]) -> str:
    """LLM 프롬프트용 섹터별 뉴스 텍스트"""
    if not sector_news:
        return "오늘의 경제 뉴스를 수집하지 못했습니다."

    lines = ["[오늘의 섹터별 주요 뉴스]"]
    for sector, articles in sector_news.items():
        lines.append(f"\n▶ {sector}")
        if not articles:
            lines.append("  (뉴스 없음)")
            continue
        for i, a in enumerate(articles, 1):
            lines.append(f"  {i}. {a['title']}")
            if a["summary"]:
                lines.append(f"     → {a['summary']}")

    return "\n".join(lines)
