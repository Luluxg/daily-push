# 每日早报自动推送

通过 GitHub Actions 定时推送天气、新闻热搜、每日一句、黄历到企业微信。

## 功能

- 🌤️ **天气** - 实时天气、温度、风力、生活指数
- 📰 **新闻热搜** - 微博热搜、知乎热榜、百度热搜
- 💡 **每日一句** - 每日名言警句
- 📅 **黄历** - 农历、干支、宜忌、冲煞

## 配置

在仓库 Settings → Secrets and variables → Actions 中添加以下 Secrets：

| Secret | 说明 | 示例 |
|--------|------|------|
| `WECHAT_WEBHOOK` | 企业微信机器人 Webhook 地址 | `https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=xxx` |
| `CITY` | 城市名称 | `北京` |
| `NEWS_COUNT` | 每条热搜显示数量（可选，默认10） | `10` |

## 推送时间

默认每天北京时间 8:00 推送（可在 `.github/workflows/daily-push.yml` 中修改 cron 表达式）。

## 手动触发

在仓库 Actions 页面点击 "Run workflow" 可手动触发推送。

## 技术栈

- Python 3.11
- GitHub Actions
- 企业微信 Webhook
- 免费 API（VVhan、一言API等）
