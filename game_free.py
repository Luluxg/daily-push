#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
游戏喜加一自动推送脚本
数据源：GamerPower API（聚合 Steam/Epic/GOG/Itch.io 等） + Epic 官方 API
推送渠道：企业微信机器人
功能：每天定时检测新的免费游戏，推送到企业微信，避免重复推送
"""

import json
import os
import time
import requests
from datetime import datetime, timezone, timedelta

# =====================================================
# 配置
# =====================================================
# 企业微信机器人 Webhook（从环境变量读取，也可以直接填写）
WECOM_WEBHOOK = os.environ.get("WECHAT_WEBHOOK", os.environ.get("WECOM_WEBHOOK", ""))

# 状态文件路径（保存已推送的游戏 ID，避免重复推送）
STATE_FILE = "game_free_state.json"

# 推送的游戏平台（可选：pc, ps4, ps5, xbox-one, xbox-series-xs, switch, android, ios, vr）
PLATFORMS = ["pc"]

# 游戏类型（可选：game, loot, beta, dlc, early-access, subscription）
GAME_TYPES = ["game", "dlc"]

# 每次最多推送多少个游戏
MAX_GAMES = 10

# =====================================================
# 工具函数
# =====================================================
def get_beijing_time():
    """获取北京时间"""
    utc_now = datetime.now(timezone.utc)
    beijing_tz = timezone(timedelta(hours=8))
    return utc_now.astimezone(beijing_tz)

def load_state():
    """加载状态文件"""
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            return {"pushed_ids": [], "last_push": ""}
    return {"pushed_ids": [], "last_push": ""}

def save_state(state):
    """保存状态文件"""
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)

def send_wecom_markdown(content):
    """发送企业微信 Markdown 消息"""
    if not WECOM_WEBHOOK:
        print("⚠️ 未配置企业微信 Webhook，跳过推送")
        return False
    
    data = {
        "msgtype": "markdown",
        "markdown": {
            "content": content
        }
    }
    
    try:
        response = requests.post(WECOM_WEBHOOK, json=data, timeout=10)
        result = response.json()
        if result.get("errcode") == 0:
            print("✅ 企业微信推送成功")
            return True
        else:
            print(f"❌ 企业微信推送失败: {result}")
            return False
    except Exception as e:
        print(f"❌ 企业微信推送异常: {e}")
        return False

def send_wecom_news(articles):
    """发送企业微信图文消息（最多8条）"""
    if not WECOM_WEBHOOK:
        print("⚠️ 未配置企业微信 Webhook，跳过推送")
        return False
    
    data = {
        "msgtype": "news",
        "news": {
            "articles": articles[:8]
        }
    }
    
    try:
        response = requests.post(WECOM_WEBHOOK, json=data, timeout=10)
        result = response.json()
        if result.get("errcode") == 0:
            print("✅ 企业微信图文推送成功")
            return True
        else:
            print(f"❌ 企业微信图文推送失败: {result}")
            return False
    except Exception as e:
        print(f"❌ 企业微信图文推送异常: {e}")
        return False

# =====================================================
# 数据获取
# =====================================================
def fetch_gamerpower_games():
    """从 GamerPower API 获取免费游戏"""
    games = []
    for platform in PLATFORMS:
        for game_type in GAME_TYPES:
            url = f"https://www.gamerpower.com/api/giveaways?platform={platform}&type={game_type}"
            try:
                response = requests.get(url, timeout=15)
                if response.status_code == 200:
                    data = response.json()
                    for item in data:
                        if item.get("status") == "Active":
                            games.append({
                                "id": f"gamerpower_{item['id']}",
                                "title": item.get("title", "未知游戏"),
                                "worth": item.get("worth", "未知"),
                                "platforms": item.get("platforms", "未知"),
                                "end_date": item.get("end_date", "未知"),
                                "description": item.get("description", ""),
                                "image": item.get("image", ""),
                                "url": item.get("open_giveaway_url", item.get("gamerpower_url", "")),
                                "source": "GamerPower"
                            })
                print(f"✅ GamerPower ({platform}/{game_type}): 获取到 {len(data)} 个游戏")
            except Exception as e:
                print(f"❌ GamerPower API 请求失败 ({platform}/{game_type}): {e}")
            time.sleep(1)
    return games

def fetch_epic_games():
    """从 Epic 官方 API 获取免费游戏"""
    games = []
    url = "https://store-site-backend-static.ak.epicgames.com/freeGamesPromotions?locale=zh-CN&country=CN&allowCountries=CN"
    try:
        response = requests.get(url, timeout=15)
        if response.status_code == 200:
            data = response.json()
            elements = data.get("data", {}).get("Catalog", {}).get("searchStore", {}).get("elements", [])
            for item in elements:
                title = item.get("title", "")
                promotions = item.get("promotions", {})
                promotional_offers = promotions.get("promotionalOffers", [])
                
                # 检查是否正在免费促销
                is_free = False
                end_date = "未知"
                for offer_group in promotional_offers:
                    for offer in offer_group.get("promotionalOffers", []):
                        discount = offer.get("discountSetting", {}).get("discountPercentage", 100)
                        if discount == 0:
                            is_free = True
                            end_date = offer.get("endDate", "未知")
                            break
                
                if is_free and title:
                    # 获取图片
                    image = ""
                    for img in item.get("keyImages", []):
                        if img.get("type") in ["OfferImageWide", "featuredMedia", "Thumbnail"]:
                            image = img.get("url", "")
                            break
                    
                    # 获取产品链接
                    product_slug = item.get("productSlug", "")
                    url = f"https://store.epicgames.com/zh-CN/p/{product_slug}" if product_slug else "https://store.epicgames.com/zh-CN/free-games"
                    
                    games.append({
                        "id": f"epic_{item['id']}",
                        "title": f"{title} (Epic Games)",
                        "worth": "免费",
                        "platforms": "PC, Epic Games Store",
                        "end_date": end_date.replace("T", " ").replace(".000Z", "") if end_date != "未知" else "未知",
                        "description": item.get("description", ""),
                        "image": image,
                        "url": url,
                        "source": "Epic"
                    })
            print(f"✅ Epic 官方 API: 获取到 {len(games)} 个免费游戏")
    except Exception as e:
        print(f"❌ Epic API 请求失败: {e}")
    return games

# =====================================================
# 主逻辑
# =====================================================
def main():
    print("=" * 60)
    print("🎮 游戏喜加一推送脚本启动")
    print(f"⏰ 北京时间: {get_beijing_time().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    
    # 1. 获取所有免费游戏
    print("\n📡 正在获取免费游戏数据...")
    all_games = []
    
    # 从 GamerPower 获取
    gamerpower_games = fetch_gamerpower_games()
    all_games.extend(gamerpower_games)
    
    # 从 Epic 官方获取
    epic_games = fetch_epic_games()
    all_games.extend(epic_games)
    
    # 去重（按标题）
    seen_titles = set()
    unique_games = []
    for game in all_games:
        title_key = game["title"].lower().strip()
        if title_key not in seen_titles:
            seen_titles.add(title_key)
            unique_games.append(game)
    
    print(f"\n📊 共获取到 {len(unique_games)} 个免费游戏（去重后）")
    
    # 2. 加载状态，过滤已推送的游戏
    state = load_state()
    pushed_ids = set(state.get("pushed_ids", []))
    
    new_games = [g for g in unique_games if g["id"] not in pushed_ids]
    print(f"🆕 其中新游戏 {len(new_games)} 个")
    
    if not new_games:
        print("✅ 没有新的免费游戏，跳过推送")
        return
    
    # 限制数量
    new_games = new_games[:MAX_GAMES]
    
    # 3. 构建推送内容（Markdown 格式）
    now_str = get_beijing_time().strftime("%Y-%m-%d %H:%M")
    
    markdown_content = f"## 🎮 游戏喜加一提醒\n\n"
    markdown_content += f"> 📅 {now_str} | 发现 {len(new_games)} 个新免费游戏\n\n"
    
    for i, game in enumerate(new_games, 1):
        markdown_content += f"### {i}. {game['title']}\n"
        markdown_content += f"- 💰 原价: {game['worth']}\n"
        markdown_content += f"- 🎯 平台: {game['platforms']}\n"
        markdown_content += f"- ⏰ 截止: {game['end_date']}\n"
        markdown_content += f"- 🔗 [点击领取]({game['url']})\n\n"
    
    markdown_content += "---\n"
    markdown_content += "*数据来源: GamerPower + Epic 官方 API*"
    
    # 4. 发送 Markdown 消息
    print("\n📤 正在推送 Markdown 消息...")
    send_wecom_markdown(markdown_content)
    
    # 5. 发送图文消息（带游戏封面图）
    print("\n📤 正在推送图文消息...")
    articles = []
    for game in new_games:
        if game.get("image"):
            articles.append({
                "title": game["title"],
                "description": f"原价: {game['worth']} | 截止: {game['end_date']}",
                "url": game["url"],
                "picurl": game["image"]
            })
    
    if articles:
        # 图文消息最多8条，分批发送
        for i in range(0, len(articles), 8):
            batch = articles[i:i+8]
            send_wecom_news(batch)
            time.sleep(1)
    
    # 6. 更新状态
    for game in new_games:
        pushed_ids.add(game["id"])
    
    state["pushed_ids"] = list(pushed_ids)
    state["last_push"] = now_str
    save_state(state)
    
    print(f"\n✅ 状态已更新，已推送 {len(pushed_ids)} 个游戏")
    print("\n🎉 游戏喜加一推送完成！")

if __name__ == "__main__":
    main()
