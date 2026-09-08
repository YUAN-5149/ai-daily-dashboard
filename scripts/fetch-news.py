#!/usr/bin/env python3
"""
AI 每日資訊自動更新腳本
GitHub Actions 每天 7:30 AM 台灣時間執行
資料來源：Google News RSS + GitHub Search API（開源專案排行）
"""
import html
import json
import os
import re
from datetime import datetime, timezone, timedelta

try:
    import feedparser
except ImportError:
    os.system("pip install feedparser -q")
    import feedparser

try:
    import requests
except ImportError:
    os.system("pip install requests -q")
    import requests

# 台灣時區 (UTC+8)
TW_TZ = timezone(timedelta(hours=8))

# RSS 來源設定
now = datetime.now(TW_TZ)
MONTH_YEAR = now.strftime("%B %Y")  # e.g. "June 2026"

RSS_FEEDS = {
    "news": [
        f"https://news.google.com/rss/search?q=AI+model+release+{MONTH_YEAR.replace(' ', '+')}&hl=en-US&gl=US&ceid=US:en",
        f"https://news.google.com/rss/search?q=Claude+GPT+Gemini+update+{MONTH_YEAR.replace(' ', '+')}&hl=en-US&gl=US&ceid=US:en",
        "https://feeds.feedburner.com/venturebeat/SZYF",
        "https://techcrunch.com/category/artificial-intelligence/feed/",
    ],
    "video": [
        f"https://news.google.com/rss/search?q=Runway+Kling+CapCut+AI+video+{MONTH_YEAR.replace(' ', '+')}&hl=en-US&gl=US&ceid=US:en",
        f"https://news.google.com/rss/search?q=AI+video+generation+tutorial+{MONTH_YEAR.replace(' ', '+')}&hl=en-US&gl=US&ceid=US:en",
    ],
    "slides": [
        f"https://news.google.com/rss/search?q=PowerPoint+Copilot+Canva+AI+slides+{MONTH_YEAR.replace(' ', '+')}&hl=en-US&gl=US&ceid=US:en",
        f"https://news.google.com/rss/search?q=Gamma+AI+presentation+{MONTH_YEAR.replace(' ', '+')}&hl=en-US&gl=US&ceid=US:en",
    ],
}

EMPTY_ITEM = {"title":"近期暫無新資訊","source":"—","date":"—","summary":"過去 7 天內尚無符合條件的新發布內容。","url":""}


def clean_html(text):
    """移除 HTML 標籤並解碼 HTML 實體（&nbsp; &amp; &#39; 等）"""
    text = re.sub(r'<[^>]+>', '', text or '')
    text = html.unescape(text)                 # &nbsp; &amp; &quot; → 實際字元
    return re.sub(r'\s+', ' ', text).strip()   # 收合多餘空白（\s 已涵蓋 nbsp）


def fetch_rss_items(feeds, max_items=12):
    """從 RSS 抓取文章"""
    items = []
    seen_urls = set()
    for url in feeds:
        try:
            feed = feedparser.parse(url)
            for entry in feed.entries:
                link = entry.get("link", "")
                if link in seen_urls:
                    continue
                seen_urls.add(link)
                items.append({
                    "title": clean_html(entry.get("title", "")),
                    "url": link,
                    "published": entry.get("published", ""),
                    "source": clean_html(feed.feed.get("title", "RSS Feed")),
                    "summary": clean_html(entry.get("summary", ""))[:400],
                })
                if len(items) >= max_items:
                    break
        except Exception as e:
            print(f"  ⚠ RSS 抓取失敗 {url[:60]}...: {e}")
    return items


def fetch_github_trending(max_items=6, days=30):
    """GitHub 開源專案排行：取近 N 天內新建、星數最高的專案"""
    since = (now - timedelta(days=days)).strftime("%Y-%m-%d")
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "ai-daily-dashboard",
    }
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"

    try:
        resp = requests.get(
            "https://api.github.com/search/repositories",
            params={"q": f"created:>{since}", "sort": "stars",
                    "order": "desc", "per_page": max_items},
            headers=headers, timeout=25,
        )
        resp.raise_for_status()
        repos = resp.json().get("items", [])
    except Exception as e:
        print(f"  ⚠ GitHub API 抓取失敗: {e}")
        return []

    out = []
    for i, r in enumerate(repos, 1):
        stars = r.get("stargazers_count", 0)
        lang = r.get("language") or "—"
        desc = clean_html(r.get("description") or "（此專案未提供說明）")
        out.append({
            "title": f"#{i} {r.get('full_name', '')} — ⭐ {stars:,}",
            "source": lang,
            "date": (r.get("created_at") or "")[:10],
            "summary": desc[:160],
            "url": r.get("html_url", ""),
        })
    return out


def main():
    categories = [
        ("news",   "AI新品與更新"),
        ("video",  "AI影片技巧"),
        ("slides", "AI簡報技巧"),
    ]

    result = {"lastUpdated": now.strftime("%Y-%m-%d %H:%M（台灣時間）"),
              "news": [], "video": [], "slides": [], "github": []}

    for key, name_zh in categories:
        print(f"\n📡 抓取 {name_zh}…")
        raw = fetch_rss_items(RSS_FEEDS[key])
        print(f"  取得 {len(raw)} 篇原始文章")
        result[key] = [{"title": it["title"], "source": it["source"],
                        "date": now.strftime("%Y-%m-%d"), "summary": it["summary"][:100],
                        "url": it["url"]} for it in raw[:6]] or [EMPTY_ITEM]
        print(f"  ✅ 整理後 {len(result[key])} 則")

    print("\n⭐ 抓取 GitHub 開源專案排行…")
    result["github"] = fetch_github_trending() or [EMPTY_ITEM]
    print(f"  ✅ 整理後 {len(result['github'])} 則")

    with open("data.json", "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    print(f"\n🎉 data.json 已更新：{result['lastUpdated']}")
    print(f"   新品 {len(result['news'])} 則 | 影片 {len(result['video'])} 則 "
          f"| 簡報 {len(result['slides'])} 則 | 開源 {len(result['github'])} 則")


if __name__ == "__main__":
    main()
