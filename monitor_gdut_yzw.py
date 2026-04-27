#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
广东工业大学研究生招生网监控脚本
监控网址: https://yzw.gdut.edu.cn/sszs.htm
功能: 每天定时发送招生网最新文章+天气问候
OAuth: 04-25 10:32:42
REDACTED_QQ_AUTH_CODE
REDACTED_QWEN_API_KEY
REDACTED_WEATHER_API_KEY
"""

import os
import smtplib
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

# ==================== 配置区域 ====================

MONITOR_URL = "https://yzw.gdut.edu.cn/sszs.htm"

# QQ邮箱配置
SMTP_SERVER = "smtp.qq.com"
SMTP_PORT = 465
SENDER_EMAIL = os.environ.get("SENDER_EMAIL", "REDACTED_SENDER_EMAIL")
SENDER_PASSWORD = os.environ.get("SENDER_PASSWORD", "REDACTED_QQ_AUTH_CODE")
RECEIVER_EMAIL = "REDACTED_RECEIVER_EMAIL"

# AI 配置（通义千问）
QWEN_API_KEY = os.environ.get("QWEN_API_KEY", "REDACTED_QWEN_API_KEY")
QWEN_MODEL = "qwen-turbo"
QWEN_API_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions"

# 天气配置（高德地图）
WEATHER_API_KEY = os.environ.get("WEATHER_API_KEY", "REDACTED_WEATHER_API_KEY")
WEATHER_API_URL = "https://restapi.amap.com/v3/weather/weatherInfo"
CITY_ADCODE = "340302"

# ==================== 日志功能 ====================

def log_message(message):
    """打印日志"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] {message}")

# ==================== 天气获取 ====================

def get_weather():
    """获取当前天气"""
    log_message(f"天气API Key: {WEATHER_API_KEY[:10]}..." if WEATHER_API_KEY else "天气API Key为空！")
    log_message(f"城市代码: {CITY_ADCODE}")

    try:
        params = {
            "key": WEATHER_API_KEY,
            "city": CITY_ADCODE,
            "extensions": "base",
            "output": "JSON"
        }
        log_message(f"请求URL: {WEATHER_API_URL}?city={CITY_ADCODE}")
        response = requests.get(WEATHER_API_URL, params=params, timeout=10)
        log_message(f"响应状态码: {response.status_code}")
        data = response.json()
        log_message(f"响应数据: {data}")

        if str(data.get("status")) == "1" and data.get("lives"):
            live = data["lives"][0]
            log_message(f"获取天气成功: {live.get('weather')}, {live.get('temperature')}°C")
            return {
                "temp": live.get("temperature", "未知"),
                "weather": live.get("weather", "未知"),
                "humidity": live.get("humidity", ""),
                "city": live.get("city", "蚌埠")
            }
        else:
            log_message(f"天气API返回错误: status={data.get('status')}, info={data.get('info')}")
    except Exception as e:
        log_message(f"获取天气失败: {e}")
    return None

# ==================== AI 问好生成 ====================

def generate_greeting(weather_info, hour):
    """根据时间和天气生成AI问好"""
    if 5 <= hour < 12:
        period = "早上"
    elif 12 <= hour < 14:
        period = "中午"
    elif 14 <= hour < 18:
        period = "下午"
    else:
        period = "晚上"

    if weather_info:
        weather_desc = f"当前{weather_info['city']}天气: {weather_info['weather']}, 温度{weather_info['temp']}°C"
        print(f"天气获取成功，{weather_desc}")
    else:
        weather_desc = "未获取到天气信息"
        print("天气获取失败")

    prompt = f"现在是{period}，{weather_desc}。请用温暖亲切的语气写一句{period}问候语，包含具体城市和具体温度和穿衣建议（冷了提醒多穿，热了提醒别中暑）。只输出问候语本身，不要加任何前缀。"

    headers = {
        "Authorization": f"Bearer {QWEN_API_KEY}",
        "Content-Type": "application/json"
    }

    payload = {
        "model": QWEN_MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": 100
    }

    try:
        response = requests.post(QWEN_API_URL, headers=headers, json=payload, timeout=30)
        if response.status_code == 200:
            return response.json()["choices"][0]["message"]["content"].strip()
    except Exception:
        pass

    temp = weather_info.get("temp", "未知") if weather_info else "未知"
    return f"{period}好！现在温度{temp}度，祝你今天愉快！"

# ==================== 网页抓取 ====================

def fetch_page(url):
    """抓取网页内容"""
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    }
    try:
        response = requests.get(url, headers=headers, timeout=30)
        response.encoding = 'utf-8'
        if response.status_code == 200:
            return response.text
    except Exception as e:
        log_message(f"请求异常: {e}")
    return None

def parse_articles(html):
    """解析网页中的文章列表"""
    soup = BeautifulSoup(html, 'html.parser')
    articles = []

    for li in soup.find_all('li', class_='no'):
        try:
            a_tag = li.find('a', href=True)
            if not a_tag:
                continue

            title = a_tag.get('title', '').strip()
            href = a_tag.get('href', '').strip()

            date_div = li.find('div', class_='tl-data')
            date_str = ""
            if date_div:
                month_day = date_div.find('p')
                year = date_div.find('span')
                if month_day and year:
                    date_str = f"{year.text}-{month_day.text}"

            summary = ""
            info_div = li.find('div', class_='tl-info2')
            if info_div:
                p_tag = info_div.find('p')
                if p_tag:
                    summary = p_tag.text.strip()

            articles.append({
                "title": title,
                "url": urljoin(MONITOR_URL, href),
                "date": date_str,
                "summary": summary[:200] + "..." if len(summary) > 200 else summary
            })
        except Exception:
            continue

    return articles

def fetch_article_html(url):
    """抓取文章详情页的完整HTML并提取正文"""
    html = fetch_page(url)
    if not html:
        return None
    try:
        soup = BeautifulSoup(html, 'html.parser')
        content_div = soup.find('div', class_='content') or soup.find('div', class_='v_news_content') or soup.find('div', id='content') or soup.find('article')
        if content_div:
            text = content_div.get_text(separator='\n', strip=True)
            return '\n'.join([line.strip() for line in text.splitlines() if line.strip()])
    except Exception:
        pass
    return None

# ==================== AI 总结 ====================

def ai_summarize(text):
    """调用通义千问API对文章内容进行总结"""
    if not text or not text.strip():
        return "（文章内容为空，无法总结）"

    max_length = 8000
    if len(text) > max_length:
        text = text[:max_length] + "..."

    headers = {
        "Authorization": f"Bearer {QWEN_API_KEY}",
        "Content-Type": "application/json"
    }

    payload = {
        "model": QWEN_MODEL,
        "messages": [
            {
                "role": "system",
                "content": "你是一个招生信息助手。请用简洁的中文总结以下内容，提取关键信息（时间、地点、要求等），不要输出任何Markdown格式符号（如*、#、-、|等），只使用纯文本和中文标点。"
            },
            {
                "role": "user",
                "content": f"请总结以下招生信息文章：\n\n{text}"
            }
        ]
    }

    try:
        response = requests.post(QWEN_API_URL, headers=headers, json=payload, timeout=60)
        if response.status_code == 200:
            summary = response.json()["choices"][0]["message"]["content"]
            # 清理Markdown格式符号
            summary = summary.replace('**', '').replace('*', '').replace('#', '').replace('---', '').replace('```', '')
            summary = summary.replace('|', ' ').replace('>', '')
            return summary
    except Exception:
        pass

    return f"（AI总结失败，原文如下）\n\n{text}"

# ==================== 邮件发送 ====================

def send_email(subject, body_text):
    """发送QQ邮件通知"""
    try:
        msg = MIMEMultipart()
        msg['From'] = SENDER_EMAIL
        msg['To'] = RECEIVER_EMAIL
        msg['Subject'] = subject
        msg.attach(MIMEText(body_text, 'plain', 'utf-8'))

        server = smtplib.SMTP_SSL(SMTP_SERVER, SMTP_PORT)
        server.login(SENDER_EMAIL, SENDER_PASSWORD)
        server.send_message(msg)
        server.quit()

        log_message("邮件发送成功！")
        return True
    except Exception as e:
        log_message(f"邮件发送失败: {e}")
        return False

# ==================== 主逻辑 ====================

def main():
    """主函数"""
    log_message("=" * 50)
    log_message("招生网监控脚本启动")
    log_message("=" * 50)


    now = datetime.now()
    current_hour = now.hour

    # 获取天气和问候语
    weather_info = get_weather()
    greeting = generate_greeting(weather_info, current_hour)

    # 获取招生网页面
    html = fetch_page(MONITOR_URL)

    articles = parse_articles(html)


    log_message(f"成功解析到 {len(articles)} 篇文章")

    # 获取第一篇文章
    first = articles[0]
    log_message(f"当前首条文章: {first['title']}")

    # 抓取正文并总结
    article_text = fetch_article_html(first['url'])
    ai_summary = ai_summarize(article_text) if article_text else "（未能提取正文内容）"

    # 组装邮件
    body = f"{greeting}\n\n"
    body += f"{'='*40}\n"
    body += "📋 【今日最新文章】\n"
    body += f"{'='*40}\n"
    body += f"标题: {first['title']}\n"
    body += f"日期: {first['date']}\n"
    body += f"链接: {first['url']}\n"
    body += f"{'='*40}\n"
    body += "【AI总结】\n"
    body += f"{'='*40}\n"
    body += ai_summary
    body += f"\n{'='*40}\n"
    body += "【原文】\n"
    body += f"{'='*40}\n"
    body += article_text if article_text else "（未能提取正文内容）"

    subject = f"【招生网】{first['title'][:30]}..."
    send_email(subject, body)

if __name__ == "__main__":
    main()
