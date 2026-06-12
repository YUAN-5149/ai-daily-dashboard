#!/usr/bin/env python3
"""
AI 每日資訊自動更新腳本
GitHub Actions 每天 7:30 AM 台灣時間執行
使用 Google News RSS + Anthropic API 抓取並翻譯 AI 最新資訊
"""
import json
import os
import sys
import re
from datetime import datetime, timezone, timedelta

try:
    import feedparser
except ImportError:
    os.system("pip install feedparser -q")
    import feedparser

try:
    import anthropic
    HAS_ANTHROPIC = True
except ImportError:
    HAS_ANTHROPIC = False

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
    """移除 HTML 標籤"""
    return re.sub(r'<[^>]+>', '', text or '').strip()


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


def translate_with_claude(client, items, category_zh, category_hint):
    """使用 Claude 翻譯與整理"""
    if not items:
        return [EMPTY_ITEM]

    raw_json = json.dumps(items, ensure_ascii=False)

    prompt = f"""以下是從 RSS 抓取的英文 AI {category_zh} 相關新聞，請：
1. 從中挑選 5~8 則**最新且最有價值**的文章（優先本月份）
2. 為每則新聞製作：
   - title：「英文原題 | 繁體中文翻譯」格式
   - source：來源媒體名稱（簡短，如 TechCrunch、Google Blog 等）
   - date：YYYY-MM-DD 格式（從 published 欄位解析，若無法解析填 {now.strftime('%Y-%m-%d')}）
   - summary：一句約 50 字的繁體中文摘要，{category_hint}
   - url：原始連結

原始資料：
{raw_json}

請只輸出合法 JSON 陣列，不要加任何說明文字：
[{{"title":"...","source":"...","date":"YYYY-MM-DD","summary":"...","url":"https://..."}}]"""

    try:
        msg = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=3000,
            messages=[{"role": "user", "content": prompt}]
        )
        text = msg.content[0].text.strip()
        start, end = text.find('['), text.rfind(']') + 1
        if start != -1 and end > start:
            result = json.loads(text[start:end])
            if result:
                return result
    except Exception as e:
        print(f"  ⚠ Claude API 錯誤: {e}")

    # 降級：直接用原始 RSS 資料（英文）
    return [{"title": it["title"], "source": it["source"],
             "date": now.strftime("%Y-%m-%d"), "summary": it["summary"][:100], "url": it["url"]}
            for it in items[:6]] or [EMPTY_ITEM]


def main():
    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    client = None
    if api_key and HAS_ANTHROPIC:
        client = anthropic.Anthropic(api_key=api_key)
        print("✅ 使用 Claude API 翻譯與整理")
    else:
        print("⚠ 未設定 ANTHROPIC_API_KEY，將使用原始英文 RSS 資料")

    categories = [
        ("news",   "AI新品與更新",   "強調重要性與對使用者的影響"),
        ("video",  "AI影片技巧",     "強調對初學者的實用性"),
        ("slides", "AI簡報技巧",     "強調對初學者的實用性"),
    ]

    result = {"lastUpdated": now.strftime("%Y-%m-%d %H:%M（台灣時間）"), "news": [], "video": [], "slides": []}

    for key, name_zh, hint in categories:
        print(f"\n📡 抓取 {name_zh}…")
        raw = fetch_rss_items(RSS_FEEDS[key])
        print(f"  取得 {len(raw)} 篇原始文章")
        if client:
            result[key] = translate_with_claude(client, raw, name_zh, hint)
        else:
            result[key] = [{"title": it["title"], "source": it["source"],
                            "date": now.strftime("%Y-%m-%d"), "summary": it["summary"][:100],
                            "url": it["url"]} for it in raw[:6]] or [EMPTY_ITEM]
        print(f"  ✅ 整理後 {len(result[key])} 則")

    with open("data.json", "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    print(f"\n🎉 data.json 已更新：{result['lastUpdated']}")
    print(f"   新品 {len(result['news'])} 則 | 影片 {len(result['video'])} 則 | 簡報 {len(result['slides'])} 則")


if __name__ == "__main__":
    main()
