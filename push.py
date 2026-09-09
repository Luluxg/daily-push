#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
每日推送脚本 - 推送到企业微信
功能：天气（含未来几天预报）、新闻热搜、每日一句
使用 GitHub Actions 定时运行
"""

import requests
import json
import os
import sys
from datetime import datetime, timedelta

# ========== 配置（从环境变量读取，在 GitHub Secrets 中配置） ==========
WECHAT_WEBHOOK = os.environ.get('WECHAT_WEBHOOK', '')  # 企业微信Webhook地址
CITY = os.environ.get('CITY', '北京')  # 城市名称
NEWS_COUNT = int(os.environ.get('NEWS_COUNT', '5'))  # 每条热搜显示数量
FORECAST_DAYS = int(os.environ.get('FORECAST_DAYS', '3'))  # 天气预报天数

# ========== 天气描述中英文映射 ==========
WEATHER_CODE_MAP = {
    0: '晴',
    1: '大部晴朗',
    2: '局部多云',
    3: '阴',
    45: '雾',
    48: '雾凇',
    51: '小毛毛雨',
    53: '毛毛雨',
    55: '大毛毛雨',
    56: '冻毛毛雨',
    57: '大冻毛毛雨',
    61: '小雨',
    63: '中雨',
    65: '大雨',
    66: '冻雨',
    67: '大冻雨',
    71: '小雪',
    73: '中雪',
    75: '大雪',
    77: '雪粒',
    80: '小阵雨',
    81: '阵雨',
    82: '强阵雨',
    85: '小阵雪',
    86: '强阵雪',
    95: '雷暴',
    96: '雷暴伴小冰雹',
    99: '雷暴伴大冰雹',
}

# 风向中英文映射
WIND_DIR_MAP = {
    'N': '北风', 'NNE': '东北偏北风', 'NE': '东北风', 'ENE': '东北偏东风',
    'E': '东风', 'ESE': '东南偏东风', 'SE': '东南风', 'SSE': '东南偏南风',
    'S': '南风', 'SSW': '西南偏南风', 'SW': '西南风', 'WSW': '西南偏西风',
    'W': '西风', 'WNW': '西北偏西风', 'NW': '西北风', 'NNW': '西北偏北风',
}

# ========== 工具函数 ==========
def safe_get(url, params=None, headers=None, timeout=15, verify=True):
    """安全的HTTP GET请求，失败返回None"""
    try:
        resp = requests.get(url, params=params, headers=headers, timeout=timeout, verify=verify)
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        print(f"  ⚠️ 请求失败: {url} - {e}")
        return None

def get_weather_code_desc(code):
    """获取天气代码的中文描述"""
    return WEATHER_CODE_MAP.get(code, f'未知({code})')

def get_wind_dir_desc(degrees):
    """获取风向的中文描述（输入为角度）"""
    # 将角度转换为16个方向的缩写
    directions = ['N', 'NNE', 'NE', 'ENE', 'E', 'ESE', 'SE', 'SSE',
                  'S', 'SSW', 'SW', 'WSW', 'W', 'WNW', 'NW', 'NNW']
    
    # 如果输入已经是字符串，直接使用
    if isinstance(degrees, str):
        return WIND_DIR_MAP.get(degrees, degrees + '风')
    
    # 将角度转换为方向索引
    try:
        idx = int((degrees + 11.25) / 22.5) % 16
        short = directions[idx]
        return WIND_DIR_MAP.get(short, short + '风')
    except Exception:
        return f"{degrees}°"

# ========== 1. 获取天气（使用 Open-Meteo，免费、无需Key、支持7天预报） ==========
def get_weather():
    """获取天气信息，包括当前天气和未来几天预报"""
    print("🌤️ 正在获取天气...")
    
    # 步骤1: 将城市名转换为经纬度（使用 Nominatim API）
    print("  📍 正在获取城市坐标...")
    geo_data = safe_get(
        'https://nominatim.openstreetmap.org/search',
        params={'q': CITY, 'format': 'json', 'limit': 1},
        headers={'User-Agent': 'DailyPushBot/1.0'}
    )
    
    if not geo_data or len(geo_data) == 0:
        print("  ⚠️ 无法获取城市坐标，使用默认坐标（北京）")
        lat, lon = 39.9042, 116.4074
        city_name = CITY
    else:
        lat = float(geo_data[0]['lat'])
        lon = float(geo_data[0]['lon'])
        city_name = geo_data[0].get('name', CITY)
        print(f"  ✅ 城市坐标获取成功: {city_name} ({lat}, {lon})")
    
    # 步骤2: 使用 Open-Meteo 获取天气
    print("  🌡️ 正在获取天气数据...")
    weather_data = safe_get(
        'https://api.open-meteo.com/v1/forecast',
        params={
            'latitude': lat,
            'longitude': lon,
            'current': 'temperature_2m,relative_humidity_2m,weather_code,wind_speed_10m,wind_direction_10m',
            'daily': 'weather_code,temperature_2m_max,temperature_2m_min,precipitation_probability_max',
            'timezone': 'auto',
            'forecast_days': FORECAST_DAYS + 1  # +1 因为包含今天
        }
    )
    
    if not weather_data:
        print("  ❌ 天气数据获取失败")
        return None
    
    # 解析当前天气
    current = weather_data.get('current', {})
    current_weather = {
        'city': city_name,
        'date': datetime.now().strftime('%Y-%m-%d'),
        'type': get_weather_code_desc(current.get('weather_code', 0)),
        'temp': f"{current.get('temperature_2m', 'N/A')}°C",
        'wind': get_wind_dir_desc(current.get('wind_direction_10m', 'N')),
        'wind_speed': f"{current.get('wind_speed_10m', 'N/A')}km/h",
        'humidity': f"{current.get('relative_humidity_2m', 'N/A')}%",
    }
    
    # 解析未来几天预报
    daily = weather_data.get('daily', {})
    forecast = []
    dates = daily.get('time', [])
    codes = daily.get('weather_code', [])
    max_temps = daily.get('temperature_2m_max', [])
    min_temps = daily.get('temperature_2m_min', [])
    precip_probs = daily.get('precipitation_probability_max', [])
    
    for i in range(1, min(FORECAST_DAYS + 1, len(dates))):  # 从第2天开始（跳过今天）
        try:
            date_obj = datetime.strptime(dates[i], '%Y-%m-%d')
            weekday = ['周一', '周二', '周三', '周四', '周五', '周六', '周日'][date_obj.weekday()]
            forecast.append({
                'date': dates[i],
                'weekday': weekday,
                'type': get_weather_code_desc(codes[i]),
                'max_temp': f"{max_temps[i]}°C",
                'min_temp': f"{min_temps[i]}°C",
                'precip_prob': f"{precip_probs[i]}%" if precip_probs[i] is not None else 'N/A',
            })
        except Exception as e:
            print(f"  ⚠️ 解析第{i}天预报失败: {e}")
    
    current_weather['forecast'] = forecast
    print(f"  ✅ 天气获取成功: {current_weather['city']} {current_weather['type']} {current_weather['temp']}")
    print(f"  📅 未来{len(forecast)}天预报已获取")
    
    return current_weather

# ========== 2. 获取新闻热搜 ==========
def get_hot_news():
    """获取多个平台的热搜榜"""
    print("📰 正在获取新闻热搜...")
    
    all_news = {}
    
    # API列表（按优先级排序）
    api_list = [
        {
            'name': '微博',
            'key': 'weibo',
            'urls': [
                'https://api.oioweb.cn/api/common/HotList',
                'https://api.vvhan.com/api/hotlist/wbHot',
            ]
        },
        {
            'name': '知乎',
            'key': 'zhihu',
            'urls': [
                'https://api.oioweb.cn/api/common/HotList',
                'https://api.vvhan.com/api/hotlist/zhihuHot',
            ]
        },
        {
            'name': '百度',
            'key': 'baidu',
            'urls': [
                'https://api.oioweb.cn/api/common/HotList',
                'https://api.vvhan.com/api/hotlist/baiduRD',
            ]
        },
    ]
    
    for api_info in api_list:
        name = api_info['name']
        key = api_info['key']
        print(f"  🔍 获取{name}热搜...")
        
        for url in api_info['urls']:
            try:
                # 对于 oioweb API，需要指定 type 参数，并禁用 SSL 验证（自签名证书）
                if 'oioweb' in url:
                    type_map = {'weibo': 'weibo', 'zhihu': 'zhihu', 'baidu': 'baidu'}
                    data = safe_get(url, params={'type': type_map.get(key, key)}, verify=False)
                else:
                    data = safe_get(url)
                
                if not data:
                    continue
                
                # 解析不同格式的返回
                items = []
                
                # 格式1: oioweb API
                if 'data' in data and isinstance(data['data'], list):
                    for item in data['data'][:NEWS_COUNT]:
                        title = item.get('title', '') or item.get('word', '') or item.get('name', '')
                        hot = item.get('hot', '') or item.get('hot_value', '') or item.get('score', '')
                        if title:
                            items.append({'title': title, 'hot': str(hot) if hot else ''})
                
                # 格式2: vvhan API
                elif data.get('success') and 'data' in data:
                    for item in data['data'][:NEWS_COUNT]:
                        title = item.get('title', '')
                        hot = item.get('hot', '')
                        if title:
                            items.append({'title': title, 'hot': str(hot) if hot else ''})
                
                if items:
                    all_news[key] = items
                    print(f"    ✅ {name}热搜获取成功: {len(items)}条")
                    break
                    
            except Exception as e:
                print(f"    ⚠️ {name}热搜获取失败: {e}")
                continue
        
        if key not in all_news:
            print(f"    ⚠️ {name}热搜获取失败")
    
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
    
    print("  ❌ 每日一句获取失败")
    return None

# ========== 4. 生成 Markdown 消息 ==========
def generate_message(weather, news, quote):
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
        msg += f"**风力**：{weather['wind']} {weather['wind_speed']}\n"
        msg += f"**湿度**：{weather['humidity']}\n"
        
        # 未来几天预报
        if weather.get('forecast') and len(weather['forecast']) > 0:
            msg += f"\n**📅 未来{len(weather['forecast'])}天预报**\n\n"
            for day in weather['forecast']:
                msg += f"- **{day['weekday']}** ({day['date']}): {day['type']}，{day['min_temp']} ~ {day['max_temp']}，降水概率 {day['precip_prob']}\n"
        
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
            for i, item in enumerate(news['weibo'][:NEWS_COUNT], 1):
                hot_str = f" ({item['hot']})" if item['hot'] else ""
                msg += f"{i}. {item['title']}{hot_str}\n"
            msg += "\n"
        
        if news.get('zhihu'):
            msg += "**💡 知乎热榜**\n"
            for i, item in enumerate(news['zhihu'][:NEWS_COUNT], 1):
                hot_str = f" ({item['hot']})" if item['hot'] else ""
                msg += f"{i}. {item['title']}{hot_str}\n"
            msg += "\n"
        
        if news.get('baidu'):
            msg += "**🔍 百度热搜**\n"
            for i, item in enumerate(news['baidu'][:NEWS_COUNT], 1):
                hot_str = f" ({item['hot']})" if item['hot'] else ""
                msg += f"{i}. {item['title']}{hot_str}\n"
            msg += "\n"
    
    # 结尾
    msg += "---\n"
    msg += f"*推送时间：{now.strftime('%Y-%m-%d %H:%M:%S')}*\n"
    msg += "*由 GitHub Actions 自动推送*"
    
    return msg

# ========== 5. 推送到企业微信 ==========
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
    print(f"📊 预报天数：{FORECAST_DAYS}天")
    print("=" * 50)
    
    # 1. 获取天气
    weather = get_weather()
    
    # 2. 获取新闻热搜
    news = get_hot_news()
    
    # 3. 获取每日一句
    quote = get_daily_quote()
    
    # 4. 生成消息
    message = generate_message(weather, news, quote)
    
    # 打印消息预览
    print("\n" + "=" * 50)
    print("📄 消息预览：")
    print("=" * 50)
    print(message[:800] + "..." if len(message) > 800 else message)
    print("=" * 50)
    
    # 5. 推送到企业微信
    success = push_to_wechat(message)
    
    if success:
        print("\n🎉 全部完成！")
        sys.exit(0)
    else:
        print("\n❌ 推送失败")
        sys.exit(1)

if __name__ == '__main__':
    main()
