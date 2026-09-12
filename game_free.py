#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
游戏优惠自动推送脚本
- Epic Games: 免费喜加一
- Steam: 打折促销（折扣>=50%，按好评排序）
推送渠道：企业微信机器人
"""

import json
import os
import time
import re
import requests
from datetime import datetime, timezone, timedelta

# =====================================================
# 配置
# =====================================================
# 企业微信机器人 Webhook
WECOM_WEBHOOK = os.environ.get("WECHAT_WEBHOOK", os.environ.get("WECOM_WEBHOOK", ""))

# 状态文件
STATE_FILE = "game_deals_state.json"

# Steam 打折配置
STEAM_MIN_DISCOUNT = 50  # 最低折扣（50%）
STEAM_MAX_GAMES = 12  # 每次最多推送多少个 Steam 打折游戏
STEAM_SORT_BY = "Reviews_DESC"  # 排序方式：Reviews_DESC（好评）、Released_DESC（最新）、Price_DESC（价格）

# Epic 免费游戏配置
EPIC_MAX_GAMES = 5  # 每次最多推送多少个 Epic 免费游戏

# =====================================================
# 工具函数
# =====================================================
def get_beijing_time():
    utc_now = datetime.now(timezone.utc)
    beijing_tz = timezone(timedelta(hours=8))
    return utc_now.astimezone(beijing_tz)

def load_state():
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            return {"pushed_epic": [], "pushed_steam": [], "last_push": ""}
    return {"pushed_epic": [], "pushed_steam": [], "last_push": ""}

def save_state(state):
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)

def send_wecom_markdown(content):
    if not WECOM_WEBHOOK:
        print("⚠️ 未配置企业微信 Webhook")
        return False
    data = {"msgtype": "markdown", "markdown": {"content": content}}
    try:
        response = requests.post(WECOM_WEBHOOK, json=data, timeout=10)
        result = response.json()
        if result.get("errcode") == 0:
            print("✅ 企业微信推送成功")
            return True
        else:
            print(f"❌ 推送失败: {result}")
            return False
    except Exception as e:
        print(f"❌ 推送异常: {e}")
        return False

def send_wecom_news(articles):
    if not WECOM_WEBHOOK:
        return False
    data = {"msgtype": "news", "news": {"articles": articles[:8]}}
    try:
        response = requests.post(WECOM_WEBHOOK, json=data, timeout=10)
        result = response.json()
        if result.get("errcode") == 0:
            print("✅ 图文推送成功")
            return True
        else:
            print(f"❌ 图文推送失败: {result}")
            return False
    except Exception as e:
        print(f"❌ 图文推送异常: {e}")
        return False

# =====================================================
# Epic 免费游戏（喜加一）
# =====================================================
def fetch_epic_free_games():
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
                    image = ""
                    for img in item.get("keyImages", []):
                        if img.get("type") in ["OfferImageWide", "featuredMedia", "Thumbnail"]:
                            image = img.get("url", "")
                            break
                    
                    product_slug = item.get("productSlug", "")
                    game_url = f"https://store.epicgames.com/zh-CN/p/{product_slug}" if product_slug else "https://store.epicgames.com/zh-CN/free-games"
                    
                    games.append({
                        "id": f"epic_{item['id']}",
                        "title": title,
                        "worth": "免费",
                        "platforms": "Epic Games Store",
                        "end_date": end_date.replace("T", " ").replace(".000Z", "") if end_date != "未知" else "未知",
                        "image": image,
                        "url": game_url,
                        "type": "epic_free"
                    })
            print(f"✅ Epic 免费游戏: {len(games)} 个")
    except Exception as e:
        print(f"❌ Epic API 失败: {e}")
    return games

# =====================================================
# Steam 打折促销
# =====================================================
def fetch_steam_deals():
    """从 Steam 获取打折游戏"""
    games = []
    
    # 1. 用搜索 API 获取特惠游戏列表（按好评排序）
    search_url = f"https://store.steampowered.com/search/results/?query&start=0&count=50&dynamic_data=&sort_by={STEAM_SORT_BY}&filter=globaltopsellers&infinite=1&l=schinese&cc=cn&specials=1"
    
    try:
        response = requests.get(search_url, timeout=15)
        if response.status_code == 200:
            data = response.json()
            html = data.get("results_html", "")
            
            # 从 HTML 中提取 appid
            appids = re.findall(r'data-ds-appid="(\d+)"', html)
            print(f"✅ Steam 搜索到 {len(appids)} 个特惠游戏")
            
            # 2. 用 appdetails API 获取每个游戏的详细信息（中文名称、价格）
            # 分批获取，每批最多 10 个（避免速率限制）
            batch_size = 10
            for i in range(0, min(len(appids), 40), batch_size):
                batch = appids[i:i+batch_size]
                appids_str = ",".join(batch)
                
                details_url = f"https://store.steampowered.com/api/appdetails?appids={appids_str}&l=schinese&cc=cn&filters=price_overview,basic"
                
                try:
                    details_response = requests.get(details_url, timeout=15)
                    if details_response.status_code == 200:
                        details_data = details_response.json()
                        
                        for appid in batch:
                            app_data = details_data.get(appid, {})
                            if not app_data.get("success"):
                                continue
                            
                            game_info = app_data.get("data", {})
                            name = game_info.get("name", "")
                            price_overview = game_info.get("price_overview", {})
                            is_free = game_info.get("is_free", False)
                            
                            if is_free:
                                continue  # 跳过免费游戏（Steam 免费的单独处理）
                            
                            discount_percent = price_overview.get("discount_percent", 0)
                            initial = price_overview.get("initial", 0)
                            final = price_overview.get("final", 0)
                            initial_formatted = price_overview.get("initial_formatted", "")
                            final_formatted = price_overview.get("final_formatted", "")
                            
                            # 筛选折扣 >= 最低折扣
                            if discount_percent >= STEAM_MIN_DISCOUNT and name:
                                # 获取游戏封面图
                                header_image = f"https://shared.akamai.steamstatic.com/store_item_assets/steam/apps/{appid}/header.jpg"
                                
                                games.append({
                                    "id": f"steam_{appid}",
                                    "title": name,
                                    "discount": discount_percent,
                                    "initial_price": initial_formatted or f"¥ {initial/100:.2f}",
                                    "final_price": final_formatted or f"¥ {final/100:.2f}",
                                    "platforms": "Steam",
                                    "image": header_image,
                                    "url": f"https://store.steampowered.com/app/{appid}/",
                                    "type": "steam_deal"
                                })
                except Exception as e:
                    print(f"❌ 获取游戏详情失败: {e}")
                
                time.sleep(1)  # 避免速率限制
                
                if len(games) >= STEAM_MAX_GAMES * 2:
                    break  # 够了就停止
            
            print(f"✅ Steam 打折游戏（>={STEAM_MIN_DISCOUNT}%）: {len(games)} 个")
    except Exception as e:
        print(f"❌ Steam 搜索失败: {e}")
    
    return games[:STEAM_MAX_GAMES]

# =====================================================
# 主逻辑
# =====================================================
def main():
    print("=" * 60)
    print("🎮 游戏优惠推送脚本启动")
    print(f"⏰ 北京时间: {get_beijing_time().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    
    state = load_state()
    pushed_epic = set(state.get("pushed_epic", []))
    pushed_steam = set(state.get("pushed_steam", []))
    
    # 1. 获取 Epic 免费游戏
    print("\n📡 获取 Epic 免费游戏...")
    epic_games = fetch_epic_free_games()
    new_epic = [g for g in epic_games if g["id"] not in pushed_epic]
    print(f"🆕 新 Epic 免费游戏: {len(new_epic)} 个")
    
    # 2. 获取 Steam 打折游戏
    print("\n📡 获取 Steam 打折游戏...")
    steam_games = fetch_steam_deals()
    new_steam = [g for g in steam_games if g["id"] not in pushed_steam]
    print(f"🆕 新 Steam 打折游戏: {len(new_steam)} 个")
    
    if not new_epic and not new_steam:
        print("✅ 没有新的游戏优惠，跳过推送")
        return
    
    now_str = get_beijing_time().strftime("%Y-%m-%d %H:%M")
    
    # 3. 构建推送内容
    markdown_content = f"## 🎮 游戏优惠提醒\n\n"
    markdown_content += f"> 📅 {now_str}\n\n"
    
    # Epic 免费游戏
    if new_epic:
        markdown_content += "### 🎁 Epic 喜加一（免费领取）\n\n"
        for i, game in enumerate(new_epic[:EPIC_MAX_GAMES], 1):
            markdown_content += f"**{i}. {game['title']}**\n"
            markdown_content += f"- ⏰ 截止: {game['end_date']}\n"
            markdown_content += f"- 🔗 [点击领取]({game['url']})\n\n"
    
    # Steam 打折游戏
    if new_steam:
        markdown_content += "### 🔥 Steam 打折促销\n\n"
        for i, game in enumerate(new_steam, 1):
            markdown_content += f"**{i}. {game['title']}**\n"
            markdown_content += f"- 💰 -{game['discount']}% | {game['initial_price']} → **{game['final_price']}**\n"
            markdown_content += f"- 🔗 [查看详情]({game['url']})\n\n"
    
    markdown_content += "---\n"
    markdown_content += "*数据来源: Epic 官方 API + Steam 官方 API*"
    
    # 4. 发送 Markdown 消息
    print("\n📤 推送 Markdown 消息...")
    send_wecom_markdown(markdown_content)
    
    # 5. 发送图文消息
    print("\n📤 推送图文消息...")
    articles = []
    
    for game in new_epic[:EPIC_MAX_GAMES]:
        if game.get("image"):
            articles.append({
                "title": f"🎁 {game['title']}",
                "description": f"免费领取 | 截止: {game['end_date']}",
                "url": game["url"],
                "picurl": game["image"]
            })
    
    for game in new_steam:
        if game.get("image"):
            articles.append({
                "title": f"🔥 -{game['discount']}% {game['title']}",
                "description": f"{game['initial_price']} → {game['final_price']}",
                "url": game["url"],
                "picurl": game["image"]
            })
    
    if articles:
        for i in range(0, len(articles), 8):
            batch = articles[i:i+8]
            send_wecom_news(batch)
            time.sleep(1)
    
    # 6. 更新状态
    for game in new_epic:
        pushed_epic.add(game["id"])
    for game in new_steam:
        pushed_steam.add(game["id"])
    
    state["pushed_epic"] = list(pushed_epic)
    state["pushed_steam"] = list(pushed_steam)
    state["last_push"] = now_str
    save_state(state)
    
    print(f"\n✅ 状态已更新")
    print("\n🎉 游戏优惠推送完成！")

if __name__ == "__main__":
    main()
