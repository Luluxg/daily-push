#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
游戏优惠自动推送脚本（增强版）
- Epic Games: 免费喜加一
- Steam: 打折促销（折扣>=50%，按好评排序）
- GOG: 免费游戏
推送渠道：企业微信、PushPlus、钉钉、飞书、Bark、Telegram
特性：多平台支持、官方API、重试机制、状态去重
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

# PushPlus（微信推送）
PUSHPLUS_TOKEN = os.environ.get("PUSHPLUS_TOKEN", "")

# 钉钉机器人 Webhook
DINGTALK_WEBHOOK = os.environ.get("DINGTALK_WEBHOOK", "")

# 飞书机器人 Webhook
FEISHU_WEBHOOK = os.environ.get("FEISHU_WEBHOOK", "")

# Bark（iOS 推送）
BARK_KEY = os.environ.get("BARK_KEY", "")

# Telegram Bot
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "")

# 状态文件
STATE_FILE = "game_deals_state.json"

# Steam 打折配置
STEAM_MIN_DISCOUNT = 50  # 最低折扣（50%）
STEAM_MAX_GAMES = 12  # 每次最多推送多少个 Steam 打折游戏
STEAM_MAX_PAGES = 3  # 最多翻几页（每页30个）
STEAM_SORT_BY = "Reviews_DESC"  # 排序方式：Reviews_DESC（好评）、Released_DESC（最新）、Price_DESC（价格）

# Epic 免费游戏配置
EPIC_MAX_GAMES = 5  # 每次最多推送多少个 Epic 免费游戏

# GOG 免费游戏配置
GOG_MAX_GAMES = 5  # 每次最多推送多少个 GOG 免费游戏

# 请求配置
REQUEST_TIMEOUT = 15
REQUEST_RETRIES = 3
REQUEST_DELAY = 1

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
            return {"pushed_epic": [], "pushed_steam": [], "pushed_gog": [], "last_push": ""}
    return {"pushed_epic": [], "pushed_steam": [], "pushed_gog": [], "last_push": ""}

def save_state(state):
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)

def request_with_retry(url, method="GET", headers=None, json_data=None, params=None):
    """带重试的请求"""
    for attempt in range(REQUEST_RETRIES):
        try:
            if method == "GET":
                response = requests.get(url, headers=headers, params=params, timeout=REQUEST_TIMEOUT)
            else:
                response = requests.post(url, headers=headers, json=json_data, timeout=REQUEST_TIMEOUT)
            return response
        except Exception as e:
            print(f"  ⚠️ 请求失败（第{attempt+1}次）: {e}")
            if attempt < REQUEST_RETRIES - 1:
                time.sleep(REQUEST_DELAY * (attempt + 1))
    return None

# =====================================================
# 多渠道推送
# =====================================================
def send_wecom_markdown(content):
    """企业微信 Markdown 推送"""
    if not WECOM_WEBHOOK:
        return False
    data = {"msgtype": "markdown", "markdown": {"content": content}}
    try:
        response = requests.post(WECOM_WEBHOOK, json=data, timeout=10)
        result = response.json()
        if result.get("errcode") == 0:
            print("✅ 企业微信推送成功")
            return True
        else:
            print(f"❌ 企业微信推送失败: {result}")
    except Exception as e:
        print(f"❌ 企业微信推送异常: {e}")
    return False

def send_wecom_news(articles):
    """企业微信图文推送"""
    if not WECOM_WEBHOOK:
        return False
    data = {"msgtype": "news", "news": {"articles": articles[:8]}}
    try:
        response = requests.post(WECOM_WEBHOOK, json=data, timeout=10)
        result = response.json()
        if result.get("errcode") == 0:
            print("✅ 企业微信图文推送成功")
            return True
    except Exception as e:
        print(f"❌ 企业微信图文推送异常: {e}")
    return False

def send_pushplus(title, content):
    """PushPlus 微信推送"""
    if not PUSHPLUS_TOKEN:
        return False
    url = f"http://www.pushplus.plus/send?token={PUSHPLUS_TOKEN}&title={title}&content={content}&template=markdown"
    try:
        response = requests.get(url, timeout=10)
        result = response.json()
        if result.get("code") == 200:
            print("✅ PushPlus 推送成功")
            return True
        else:
            print(f"❌ PushPlus 推送失败: {result}")
    except Exception as e:
        print(f"❌ PushPlus 推送异常: {e}")
    return False

def send_dingtalk_markdown(title, content):
    """钉钉 Markdown 推送"""
    if not DINGTALK_WEBHOOK:
        return False
    data = {
        "msgtype": "markdown",
        "markdown": {
            "title": title,
            "text": content
        }
    }
    try:
        response = requests.post(DINGTALK_WEBHOOK, json=data, timeout=10)
        result = response.json()
        if result.get("errcode") == 0:
            print("✅ 钉钉推送成功")
            return True
        else:
            print(f"❌ 钉钉推送失败: {result}")
    except Exception as e:
        print(f"❌ 钉钉推送异常: {e}")
    return False

def send_feishu_text(content):
    """飞书文本推送"""
    if not FEISHU_WEBHOOK:
        return False
    data = {
        "msg_type": "text",
        "content": {
            "text": content
        }
    }
    try:
        response = requests.post(FEISHU_WEBHOOK, json=data, timeout=10)
        result = response.json()
        if result.get("code") == 0 or result.get("StatusCode") == 0:
            print("✅ 飞书推送成功")
            return True
        else:
            print(f"❌ 飞书推送失败: {result}")
    except Exception as e:
        print(f"❌ 飞书推送异常: {e}")
    return False

def send_bark(title, content, url=""):
    """Bark iOS 推送"""
    if not BARK_KEY:
        return False
    push_url = f"https://api.day.app/{BARK_KEY}/{title}/{content}"
    if url:
        push_url += f"?url={url}"
    try:
        response = requests.get(push_url, timeout=10)
        result = response.json()
        if result.get("code") == 200:
            print("✅ Bark 推送成功")
            return True
        else:
            print(f"❌ Bark 推送失败: {result}")
    except Exception as e:
        print(f"❌ Bark 推送异常: {e}")
    return False

def send_telegram(text):
    """Telegram 推送"""
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        return False
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    data = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": text,
        "parse_mode": "Markdown",
        "disable_web_page_preview": False
    }
    try:
        response = requests.post(url, json=data, timeout=10)
        result = response.json()
        if result.get("ok"):
            print("✅ Telegram 推送成功")
            return True
        else:
            print(f"❌ Telegram 推送失败: {result}")
    except Exception as e:
        print(f"❌ Telegram 推送异常: {e}")
    return False

def send_all_channels(title, markdown_content, plain_text="", articles=None):
    """推送到所有已配置的渠道"""
    print("\n📤 开始多渠道推送...")
    
    # 企业微信
    if WECOM_WEBHOOK:
        send_wecom_markdown(markdown_content)
        if articles:
            for i in range(0, len(articles), 8):
                send_wecom_news(articles[i:i+8])
                time.sleep(1)
    
    # PushPlus
    if PUSHPLUS_TOKEN:
        send_pushplus(title, markdown_content)
    
    # 钉钉
    if DINGTALK_WEBHOOK:
        send_dingtalk_markdown(title, markdown_content)
    
    # 飞书
    if FEISHU_WEBHOOK:
        send_feishu_text(plain_text or markdown_content)
    
    # Bark
    if BARK_KEY:
        send_bark(title, plain_text or "游戏优惠已更新，点击查看详情")
    
    # Telegram
    if TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID:
        send_telegram(plain_text or markdown_content)
    
    print("✅ 多渠道推送完成")

# =====================================================
# Epic 免费游戏（喜加一）
# =====================================================
def fetch_epic_free_games():
    """从 Epic 官方 API 获取免费游戏"""
    games = []
    url = "https://store-site-backend-static.ak.epicgames.com/freeGamesPromotions?locale=zh-CN&country=CN&allowCountries=CN"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept": "application/json"
    }
    try:
        response = request_with_retry(url, headers=headers)
        if response and response.status_code == 200:
            data = response.json()
            elements = data.get("data", {}).get("Catalog", {}).get("searchStore", {}).get("elements", [])
            for item in elements:
                title = item.get("title", "")
                promotions = item.get("promotions") or {}
                promotional_offers = promotions.get("promotionalOffers", []) or []
                
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
    """从 Steam 获取打折游戏（官方 API）"""
    games = []
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept": "application/json"
    }
    
    # 方法1: 使用 featuredcategories 获取特惠
    try:
        print("  尝试 Steam featuredcategories API...")
        featured_url = "https://store.steampowered.com/api/featuredcategories/?l=schinese&cc=cn"
        response = request_with_retry(featured_url, headers=headers)
        print(f"  featuredcategories 状态码: {response.status_code if response else 'None'}")
        
        if response and response.status_code == 200:
            data = response.json()
            for cat_id, cat_data in data.items():
                if isinstance(cat_data, dict) and "items" in cat_data:
                    items = cat_data.get("items", [])
                    for item in items:
                        if item.get("discount_percent", 0) >= STEAM_MIN_DISCOUNT:
                            appid = item.get("id")
                            name = item.get("name", "")
                            if appid and name:
                                games.append({
                                    "id": f"steam_{appid}",
                                    "title": name,
                                    "discount": item.get("discount_percent", 0),
                                    "initial_price": item.get("original_price", ""),
                                    "final_price": item.get("final_price", ""),
                                    "platforms": "Steam",
                                    "image": item.get("header_image", item.get("large_capsule_image", "")),
                                    "url": f"https://store.steampowered.com/app/{appid}/",
                                    "type": "steam_deal"
                                })
            print(f"  featuredcategories 获取到 {len(games)} 个打折游戏")
    except Exception as e:
        print(f"  featuredcategories 失败: {e}")
    
    # 方法2: 如果方法1获取的不够，用搜索 API + appdetails（支持翻页）
    if len(games) < STEAM_MAX_GAMES:
        try:
            print(f"  尝试 Steam 搜索 API（最多翻 {STEAM_MAX_PAGES} 页）...")
            all_appids = []
            
            # 翻页获取
            for page in range(STEAM_MAX_PAGES):
                start = page * 30
                search_url = f"https://store.steampowered.com/search/results/?query&start={start}&count=30&dynamic_data=&sort_by={STEAM_SORT_BY}&filter=globaltopsellers&infinite=1&l=schinese&cc=cn&specials=1"
                response = request_with_retry(search_url, headers=headers)
                
                if response and response.status_code == 200:
                    data = response.json()
                    html = data.get("results_html", "")
                    page_appids = re.findall(r'data-ds-appid="(\d+)"', html)
                    print(f"  第{page+1}页: 找到 {len(page_appids)} 个特惠游戏 appid")
                    all_appids.extend(page_appids)
                    
                    # 如果这一页没有数据，停止翻页
                    if len(page_appids) == 0:
                        break
                else:
                    print(f"  第{page+1}页获取失败，停止翻页")
                    break
                
                time.sleep(1)  # 翻页间隔
            
            print(f"  总共找到 {len(all_appids)} 个特惠游戏 appid")
            
            # 去重
            all_appids = list(dict.fromkeys(all_appids))
            
            # 批量获取详情（官方 appdetails API）
            batch_size = 5
            for i in range(0, min(len(all_appids), 50), batch_size):
                batch = all_appids[i:i+batch_size]
                appids_str = ",".join(batch)
                details_url = f"https://store.steampowered.com/api/appdetails?appids={appids_str}&l=schinese&cc=cn&filters=price_overview,basic"
                
                try:
                    details_response = request_with_retry(details_url, headers=headers)
                    if details_response and details_response.status_code == 200:
                        details_data = details_response.json()
                        for appid in batch:
                            app_data = details_data.get(appid, {})
                            if not app_data.get("success"):
                                continue
                            game_info = app_data.get("data", {})
                            name = game_info.get("name", "")
                            price_overview = game_info.get("price_overview", {})
                            is_free = game_info.get("is_free", False)
                            
                            if is_free or not name:
                                continue
                            
                            discount_percent = price_overview.get("discount_percent", 0)
                            if discount_percent >= STEAM_MIN_DISCOUNT:
                                header_image = f"https://shared.akamai.steamstatic.com/store_item_assets/steam/apps/{appid}/header.jpg"
                                games.append({
                                    "id": f"steam_{appid}",
                                    "title": name,
                                    "discount": discount_percent,
                                    "initial_price": price_overview.get("initial_formatted", f"¥{price_overview.get('initial',0)/100:.0f}"),
                                    "final_price": price_overview.get("final_formatted", f"¥{price_overview.get('final',0)/100:.0f}"),
                                    "platforms": "Steam",
                                    "image": header_image,
                                    "url": f"https://store.steampowered.com/app/{appid}/",
                                    "type": "steam_deal"
                                })
                except Exception as e:
                    print(f"  获取详情失败: {e}")
                time.sleep(1)
                
                if len(games) >= STEAM_MAX_GAMES * 2:
                    break
        except Exception as e:
            print(f"  搜索 API 失败: {e}")
    
    # 去重
    seen = set()
    unique_games = []
    for game in games:
        if game["id"] not in seen:
            seen.add(game["id"])
            unique_games.append(game)
    
    print(f"✅ Steam 打折游戏（>={STEAM_MIN_DISCOUNT}%）: {len(unique_games)} 个")
    return unique_games[:STEAM_MAX_GAMES]

# =====================================================
# GOG 免费游戏
# =====================================================
def fetch_gog_free_games():
    """从 GOG 获取免费游戏"""
    games = []
    url = "https://www.gog.com/games/ajax/filtered?mediaType=game&price=free&sort=popularity"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept": "application/json"
    }
    try:
        response = request_with_retry(url, headers=headers)
        if response and response.status_code == 200:
            data = response.json()
            products = data.get("products", [])
            for item in products[:GOG_MAX_GAMES * 2]:
                title = item.get("title", "")
                if not title:
                    continue
                
                game_id = item.get("id", "")
                slug = item.get("slug", "")
                image = item.get("image", "")
                if image and not image.startswith("http"):
                    image = "https:" + image
                
                game_url = f"https://www.gog.com/game/{slug}" if slug else "https://www.gog.com/"
                
                games.append({
                    "id": f"gog_{game_id}",
                    "title": title,
                    "worth": "免费",
                    "platforms": "GOG",
                    "end_date": "限时免费",
                    "image": image,
                    "url": game_url,
                    "type": "gog_free"
                })
            print(f"✅ GOG 免费游戏: {len(games)} 个")
    except Exception as e:
        print(f"❌ GOG API 失败: {e}")
    return games[:GOG_MAX_GAMES]

# =====================================================
# 主逻辑
# =====================================================
def main():
    print("=" * 60)
    print("🎮 游戏优惠推送脚本（增强版）启动")
    print(f"⏰ 北京时间: {get_beijing_time().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    
    # 打印已配置的推送渠道
    channels = []
    if WECOM_WEBHOOK: channels.append("企业微信")
    if PUSHPLUS_TOKEN: channels.append("PushPlus")
    if DINGTALK_WEBHOOK: channels.append("钉钉")
    if FEISHU_WEBHOOK: channels.append("飞书")
    if BARK_KEY: channels.append("Bark")
    if TELEGRAM_BOT_TOKEN: channels.append("Telegram")
    print(f"📱 已配置推送渠道: {', '.join(channels) if channels else '无'}")
    
    state = load_state()
    pushed_epic = set(state.get("pushed_epic", []))
    pushed_steam = set(state.get("pushed_steam", []))
    pushed_gog = set(state.get("pushed_gog", []))
    
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
    
    # 3. 获取 GOG 免费游戏
    print("\n📡 获取 GOG 免费游戏...")
    gog_games = fetch_gog_free_games()
    new_gog = [g for g in gog_games if g["id"] not in pushed_gog]
    print(f"🆕 新 GOG 免费游戏: {len(new_gog)} 个")
    
    now_str = get_beijing_time().strftime("%Y-%m-%d %H:%M")
    
    if not new_epic and not new_steam and not new_gog:
        print("✅ 没有新的游戏优惠，跳过推送")
        state["last_push"] = now_str
        save_state(state)
        return
    
    # 4. 构建推送内容
    title = "🎮 游戏优惠提醒"
    
    markdown_content = f"## 🎮 游戏优惠提醒\n\n"
    markdown_content += f"> 📅 {now_str}\n\n"
    
    plain_text = f"🎮 游戏优惠提醒 ({now_str})\n\n"
    
    # Epic 免费游戏
    if new_epic:
        markdown_content += "### 🎁 Epic 喜加一（免费领取）\n\n"
        plain_text += "🎁 Epic 喜加一（免费领取）\n"
        for i, game in enumerate(new_epic[:EPIC_MAX_GAMES], 1):
            markdown_content += f"**{i}. {game['title']}**\n"
            markdown_content += f"- ⏰ 截止: {game['end_date']}\n"
            markdown_content += f"- 🔗 [点击领取]({game['url']})\n\n"
            plain_text += f"{i}. {game['title']} - 截止: {game['end_date']}\n   {game['url']}\n"
    
    # Steam 打折游戏
    if new_steam:
        markdown_content += "### 🔥 Steam 打折促销\n\n"
        plain_text += "\n🔥 Steam 打折促销\n"
        for i, game in enumerate(new_steam, 1):
            markdown_content += f"**{i}. {game['title']}**\n"
            markdown_content += f"- 💰 -{game['discount']}% | {game['initial_price']} → **{game['final_price']}**\n"
            markdown_content += f"- 🔗 [查看详情]({game['url']})\n\n"
            plain_text += f"{i}. {game['title']} - -{game['discount']}% | {game['initial_price']} → {game['final_price']}\n   {game['url']}\n"
    
    # GOG 免费游戏
    if new_gog:
        markdown_content += "### 🎮 GOG 免费游戏\n\n"
        plain_text += "\n🎮 GOG 免费游戏\n"
        for i, game in enumerate(new_gog[:GOG_MAX_GAMES], 1):
            markdown_content += f"**{i}. {game['title']}**\n"
            markdown_content += f"- ⏰ {game['end_date']}\n"
            markdown_content += f"- 🔗 [点击领取]({game['url']})\n\n"
            plain_text += f"{i}. {game['title']} - {game['end_date']}\n   {game['url']}\n"
    
    markdown_content += "---\n"
    markdown_content += "*数据来源: Epic 官方 API + Steam 官方 API + GOG 官方 API*"
    
    # 5. 构建图文消息
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
    
    for game in new_gog[:GOG_MAX_GAMES]:
        if game.get("image"):
            articles.append({
                "title": f"🎮 {game['title']}",
                "description": "GOG 免费领取",
                "url": game["url"],
                "picurl": game["image"]
            })
    
    # 6. 多渠道推送
    send_all_channels(title, markdown_content, plain_text, articles)
    
    # 7. 更新状态
    for game in new_epic:
        pushed_epic.add(game["id"])
    for game in new_steam:
        pushed_steam.add(game["id"])
    for game in new_gog:
        pushed_gog.add(game["id"])
    
    state["pushed_epic"] = list(pushed_epic)
    state["pushed_steam"] = list(pushed_steam)
    state["pushed_gog"] = list(pushed_gog)
    state["last_push"] = now_str
    save_state(state)
    
    print(f"\n✅ 状态已更新")
    print("\n🎉 游戏优惠推送完成！")

if __name__ == "__main__":
    main()
