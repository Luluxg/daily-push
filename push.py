#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
每日推送脚本 - 推送到企业微信
功能：天气、新闻热搜、每日一句、黄历
使用 GitHub Actions 定时运行
"""

import requests
import json
import os
import sys
from datetime import datetime

# ========== 配置（从环境变量读取，在 GitHub Secrets 中配置） ==========
WECHAT_WEBHOOK = os.environ.get('WECHAT_WEBHOOK', '')  # 企业微信Webhook地址
CITY = os.environ.get('CITY', '北京')  # 城市名称
NEWS_COUNT = int(os.environ.get('NEWS_COUNT', '10'))  # 每条热搜显示数量

# ========== 工具函数 ==========
def safe_get(url, params=None, headers=None, timeout=15):
    """安全的HTTP GET请求，失败返回None"""
    try:
        resp = requests.get(url, params=params, headers=headers, timeout=timeout)
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        print(f"  ⚠️ 请求失败: {url} - {e}")
        return None

# ========== 1. 获取天气 ==========
def get_weather():
    """获取天气信息，使用多个备用API"""
    print("🌤️ 正在获取天气...")
    
    # API1: VVhan 天气API（免费，不需要Key）
    try:
        data = safe_get(f'https://api.vvhan.com/api/weather', params={'city': CITY})
        if data and data.get('success'):
            info = data.get('data', {})
            weather = {
                'city': info.get('city', CITY),
                'date': info.get('date', ''),
                'week': info.get('week', ''),
                'type': info.get('type', ''),
                'temp': info.get('temp', ''),
                'temp_range': info.get('low', '') + ' ~ ' + info.get('high', ''),
                'wind': info.get('wind', ''),
                'wind_speed': info.get('windSpeed', ''),
                'humidity': info.get('humidity', ''),
                'air': info.get('air', {}).get('level', '') if isinstance(info.get('air'), dict) else info.get('air', ''),
                'tips': info.get('tips', ''),
            }
            print(f"  ✅ 天气获取成功: {weather['city']} {weather['type']} {weather['temp']}")
            return weather
    except Exception as e:
        print(f"  ⚠️ VVhan天气API失败: {e}")
    
    # API2: 备用天气API
    try:
        data = safe_get(f'https://wttr.in/{CITY}', params={'format': 'j1', 'lang': 'zh'})
        if data:
            current = data.get('current_condition', [{}])[0]
            weather = {
                'city': CITY,
                'date': datetime.now().strftime('%Y-%m-%d'),
                'week': '',
                'type': current.get('lang_zh', [{}])[0].get('value', current.get('weatherDesc', [{}])[0].get('value', '')),
                'temp': current.get('temp_C', '') + '°C',
                'temp_range': '',
                'wind': current.get('winddir16Point', '') + '风',
                'wind_speed': current.get('windspeedKmph', '') + 'km/h',
                'humidity': current.get('humidity', '') + '%',
                'air': '',
                'tips': '',
            }
            print(f"  ✅ 备用天气获取成功: {weather['type']} {weather['temp']}")
            return weather
    except Exception as e:
        print(f"  ⚠️ 备用天气API失败: {e}")
    
    print("  ❌ 所有天气API均失败")
    return None

# ========== 2. 获取新闻热搜 ==========
def get_hot_news():
    """获取多个平台的热搜榜"""
    print("📰 正在获取新闻热搜...")
    
    all_news = {}
    
    # 微博热搜
    print("  🔍 获取微博热搜...")
    data = safe_get('https://api.vvhan.com/api/hotlist/wbHot')
    if data and data.get('success'):
        items = data.get('data', [])[:NEWS_COUNT]
        all_news['weibo'] = [{'title': item.get('title', ''), 'hot': item.get('hot', '')} for item in items]
        print(f"    ✅ 微博热搜: {len(all_news['weibo'])}条")
    else:
        print("    ⚠️ 微博热搜获取失败")
    
    # 知乎热榜
    print("  🔍 获取知乎热榜...")
    data = safe_get('https://api.vvhan.com/api/hotlist/zhihuHot')
    if data and data.get('success'):
        items = data.get('data', [])[:NEWS_COUNT]
        all_news['zhihu'] = [{'title': item.get('title', ''), 'hot': item.get('hot', '')} for item in items]
        print(f"    ✅ 知乎热榜: {len(all_news['zhihu'])}条")
    else:
        print("    ⚠️ 知乎热榜获取失败")
    
    # 百度热搜
    print("  🔍 获取百度热搜...")
    data = safe_get('https://api.vvhan.com/api/hotlist/baiduRD')
    if data and data.get('success'):
        items = data.get('data', [])[:NEWS_COUNT]
        all_news['baidu'] = [{'title': item.get('title', ''), 'hot': item.get('hot', '')} for item in items]
        print(f"    ✅ 百度热搜: {len(all_news['baidu'])}条")
    else:
        print("    ⚠️ 百度热搜获取失败")
    
    return all_news

# ========== 3. 获取每日一句 ==========
def get_daily_quote():
    """获取每日一句，使用一言API"""
    print("💡 正在获取每日一句...")
    
    # API1: 一言API
    data = safe_get('https://v1.hitokoto.cn/', params={'c': 'i', 'encode': 'json'})
    if data:
        quote = {
            'text': data.get('hitokoto', ''),
            'from': data.get('from', ''),
            'from_who': data.get('from_who', ''),
        }
        print(f"  ✅ 每日一句获取成功: {quote['text'][:20]}...")
        return quote
    
    # API2: 备用
    data = safe_get('https://api.vvhan.com/api/ian/rand')
    if data and data.get('success'):
        quote = {
            'text': data.get('data', {}).get('title', ''),
            'from': '',
            'from_who': '',
        }
        print(f"  ✅ 备用每日一句获取成功")
        return quote
    
    print("  ❌ 每日一句获取失败")
    return None

# ========== 4. 获取黄历 ==========
def get_huangli():
    """获取今日黄历"""
    print("📅 正在获取黄历...")
    
    data = safe_get('https://api.vvhan.com/api/huangli')
    if data and data.get('success'):
        info = data.get('data', {})
        huangli = {
            'date': info.get('date', ''),
            'lunar': info.get('lunar', ''),
            'ganzhi': info.get('ganzhi', ''),
            'zodiac': info.get('zodiac', ''),
            'star': info.get('star', ''),
            'yi': info.get('yi', []),  # 宜
            'ji': info.get('ji', []),  # 忌
            'taishen': info.get('taishen', ''),
            'chongsha': info.get('chongsha', ''),
            'wuxing': info.get('wuxing', ''),
        }
        print(f"  ✅ 黄历获取成功: {huangli['lunar']}")
        return huangli
    
    print("  ⚠️ 黄历获取失败")
    return None

# ========== 5. 生成 Markdown 消息 ==========
def generate_message(weather, news, quote, huangli):
    """生成企业微信 Markdown 格式的消息"""
    print("✍️ 正在生成消息...")
    
    now = datetime.now()
    date_str = now.strftime('%Y年%m月%d日')
    week_list = ['星期一', '星期二', '星期三', '星期四', '星期五', '星期六', '星期日']
    week_str = week_list[now.weekday()]
    
    msg = f"### 🌅 每日早报 | {date_str} {week_str}\n\n"
    
    # ---- 天气部分 ----
    if weather:
        msg += "#### 🌤️ 今日天气\n\n"
        msg += f"**城市**：{weather['city']}\n"
        msg += f"**天气**：{weather['type']} {weather['temp']}\n"
        if weather['temp_range']:
            msg += f"**温度**：{weather['temp_range']}\n"
        if weather['wind']:
            msg += f"**风力**：{weather['wind']} {weather['wind_speed']}\n"
        if weather['humidity']:
            msg += f"**湿度**：{weather['humidity']}\n"
        if weather['air']:
            msg += f"**空气质量**：{weather['air']}\n"
        if weather['tips']:
            msg += f"**温馨提示**：{weather['tips']}\n"
        msg += "\n"
    
    # ---- 黄历部分 ----
    if huangli:
        msg += "#### 📅 今日黄历\n\n"
        msg += f"**农历**：{huangli['lunar']}\n"
        msg += f"**干支**：{huangli['ganzhi']} 【{huangli['zodiac']}】\n"
        if huangli['star']:
            msg += f"**星座**：{huangli['star']}\n"
        if huangli['chongsha']:
            msg += f"**冲煞**：{huangli['chongsha']}\n"
        if huangli['yi']:
            yi_str = '、'.join(huangli['yi'][:8]) if isinstance(huangli['yi'], list) else huangli['yi']
            msg += f"**宜**：{yi_str}\n"
        if huangli['ji']:
            ji_str = '、'.join(huangli['ji'][:8]) if isinstance(huangli['ji'], list) else huangli['ji']
            msg += f"**忌**：{ji_str}\n"
        msg += "\n"
    
    # ---- 每日一句 ----
    if quote:
        msg += "#### 💡 每日一句\n\n"
        msg += f"> {quote['text']}\n"
        if quote['from'] or quote['from_who']:
            author = quote['from_who'] or quote['from']
            msg += f"> —— {author}\n"
        msg += "\n"
    
    # ---- 新闻热搜 ----
    if news:
        msg += "#### 📰 今日热搜\n\n"
        
        if news.get('weibo'):
            msg += "**🔥 微博热搜**\n"
            for i, item in enumerate(news['weibo'][:5], 1):
                hot_str = f" ({item['hot']})" if item['hot'] else ""
                msg += f"{i}. {item['title']}{hot_str}\n"
            msg += "\n"
        
        if news.get('zhihu'):
            msg += "**💡 知乎热榜**\n"
            for i, item in enumerate(news['zhihu'][:5], 1):
                hot_str = f" ({item['hot']})" if item['hot'] else ""
                msg += f"{i}. {item['title']}{hot_str}\n"
            msg += "\n"
        
        if news.get('baidu'):
            msg += "**🔍 百度热搜**\n"
            for i, item in enumerate(news['baidu'][:5], 1):
                hot_str = f" ({item['hot']})" if item['hot'] else ""
                msg += f"{i}. {item['title']}{hot_str}\n"
            msg += "\n"
    
    # 结尾
    msg += "---\n"
    msg += f"*推送时间：{now.strftime('%Y-%m-%d %H:%M:%S')}*\n"
    msg += "*由 GitHub Actions 自动推送*"
    
    return msg

# ========== 6. 推送到企业微信 ==========
def push_to_wechat(message):
    """推送到企业微信"""
    print("📤 正在推送到企业微信...")
    
    if not WECHAT_WEBHOOK:
        print("  ❌ 未配置 WECHAT_WEBHOOK 环境变量")
        return False
    
    payload = {
        'msgtype': 'markdown',
        'markdown': {
            'content': message
        }
    }
    
    try:
        resp = requests.post(WECHAT_WEBHOOK, json=payload, timeout=15)
        result = resp.json()
        if result.get('errcode') == 0:
            print("  ✅ 推送成功！")
            return True
        else:
            print(f"  ❌ 推送失败: {result}")
            return False
    except Exception as e:
        print(f"  ❌ 推送异常: {e}")
        return False

# ========== 主函数 ==========
def main():
    print("=" * 50)
    print("🚀 每日推送脚本启动")
    print(f"📅 时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"📍 城市：{CITY}")
    print("=" * 50)
    
    # 1. 获取天气
    weather = get_weather()
    
    # 2. 获取新闻热搜
    news = get_hot_news()
    
    # 3. 获取每日一句
    quote = get_daily_quote()
    
    # 4. 获取黄历
    huangli = get_huangli()
    
    # 5. 生成消息
    message = generate_message(weather, news, quote, huangli)
    
    # 打印消息预览
    print("\n" + "=" * 50)
    print("📄 消息预览：")
    print("=" * 50)
    print(message[:500] + "..." if len(message) > 500 else message)
    print("=" * 50)
    
    # 6. 推送到企业微信
    success = push_to_wechat(message)
    
    if success:
        print("\n🎉 全部完成！")
        sys.exit(0)
    else:
        print("\n❌ 推送失败")
        sys.exit(1)

if __name__ == '__main__':
    main()
