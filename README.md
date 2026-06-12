# AI課每日資訊看板

> 每天自動更新的 AI 新品、影片技巧、簡報技巧彙整看板

🔗 **線上網址**：https://YUAN-5149.github.io/ai-daily-dashboard/

## 功能

- 📋 三大分類：AI新品與更新、AI影片技巧、AI簡報技巧
- 🔍 即時搜尋過濾
- ⏰ 每天台灣時間 07:30 自動更新
- 📱 支援手機與桌面

## 自動更新說明

本專案使用 GitHub Actions 每天自動執行 `scripts/fetch-news.py`：
1. 從 Google News RSS 抓取最新 AI 相關新聞
2. 使用 Anthropic Claude API 翻譯並整理成繁體中文摘要
3. 更新 `data.json` 並推送到 GitHub
4. GitHub Pages 自動提供最新版本給瀏覽器

## 設定方式

### 設定 ANTHROPIC_API_KEY（取得中文翻譯與 AI 摘要）

至 GitHub Repo → Settings → Secrets and variables → Actions → 新增：
- Name: `ANTHROPIC_API_KEY`
- Value: 你的 Anthropic API 金鑰（可從 https://console.anthropic.com 取得）

> 若未設定此金鑰，系統仍會更新資料，但內容為英文原文。

### 手動觸發更新

至 GitHub Repo → Actions → 每日更新 AI 資訊看板 → Run workflow

### 啟用 GitHub Pages

至 Repo → Settings → Pages → Source: Deploy from a branch → Branch: main / (root) → Save

公開網址：https://YUAN-5149.github.io/ai-daily-dashboard/
