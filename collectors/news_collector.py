"""경제 뉴스 RSS 수집"""
import feedparser
from typing import Any


# 무료 RSS 피드 목록
NEWS_FEEDS = {
    "한국경제": "https://www.hankyung.com/feed/economy",
    "연합뉴스_경제": "https://www.yonhapnewstv.co.kr/browse/feed/category/economy",
    "매일경제": "https://www.mk.co.kr/rss/30100041/",
}

# 대체 피드 (위 피드가 불안정할 경우)
FALLBACK_FEEDS = {
    "Google뉴스_경제": "https://news.google.com/rss/search?q=한국+경제&hl=ko&gl=KR&ceid=KR:ko",
    "Google뉴스_증시": "https://news.google.com/rss/search?q=한국+증시&hl=ko&gl=KR&ceid=KR:ko",
}


def fetch_news(max_items: int = 5) -> list[dict[str, Any]]:
    """
    경제 뉴스 수집 (최대 max_items * 피드 수)
    """
    articles = []

    for source, url in NEWS_FEEDS.items():
        try:
            feed = feedparser.parse(url)
            for entry in feed.entries[:max_items]:
                articles.append({
                    "source": source,
                    "title": entry.get("title", "제목 없음"),
                    "link": entry.get("link", ""),
                    "published": entry.get("published", ""),
                    "summary": _clean_summary(entry.get("summary", "")),
                })
        except Exception:
            continue

    # 피드에서 아무것도 못 가져온 경우 대체 피드 사용
    if not articles:
        for source, url in FALLBACK_FEEDS.items():
            try:
                feed = feedparser.parse(url)
                for entry in feed.entries[:max_items]:
                    articles.append({
                        "source": source,
                        "title": entry.get("title", ""),
                        "link": entry.get("link", ""),
                        "published": entry.get("published", ""),
                        "summary": _clean_summary(entry.get("summary", "")),
                    })
            except Exception:
                continue

    return articles


def _clean_summary(text: str) -> str:
    """HTML 태그 제거 및 길이 제한"""
    import re
    clean = re.sub(r"<[^>]+>", "", text)
    clean = clean.strip()
    if len(clean) > 200:
        clean = clean[:200] + "..."
    return clean


def format_news_for_prompt(articles: list[dict]) -> str:
    """LLM 프롬프트용 뉴스 텍스트 포맷"""
    if not articles:
        return "오늘의 경제 뉴스를 수집하지 못했습니다."

    lines = ["[오늘의 주요 경제 뉴스]"]
    for i, a in enumerate(articles[:10], 1):  # 최대 10개
        lines.append(f"{i}. [{a['source']}] {a['title']}")
        if a["summary"]:
            lines.append(f"   요약: {a['summary']}")
    return "\n".join(lines)
