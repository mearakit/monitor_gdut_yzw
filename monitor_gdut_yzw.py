#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
广东工业大学研究生招生网监控脚本
监控网址: https://yzw.gdut.edu.cn/sszs.htm
功能: 监控页面更新，结合天气和AI问好，发送邮件通知
"""

import hashlib
import json
import os
import smtplib
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

# ==================== 配置区域 ====================

# 监控配置
MONITOR_URL = "https://yzw.gdut.edu.cn/sszs.htm"
DATA_FILE = "monitor_data.json"
"""
Name:           SENDER_EMAIL                                                                                                                                                                     █  
     Secret:         REDACTED_SENDER_EMAIL                                                                                                                           Context                              █  
                                                                                                                                                                 46,528 tokens                        █  
     Name:           SENDER_PASSWORD                                                                                                                             18% used                             █  
     Secret:         REDACTED_QQ_AUTH_CODE                                                                                                                            $0.00 spent                          █  
                                                                                                                                                                                                      █  
     Name:           RECEIVER_EMAIL                                                                                                                              LSP                                  █  
     Secret:         REDACTED_SENDER_EMAIL                                                                                                                           LSPs will activate as files are read █  
                                                                                                                                                                                                      █  
     Name:           QWEN_API_KEY                                                                                                                                ▼ Todo                               █  
     Secret:         REDACTED_QWEN_API_KEY   
      
      """
# QQ邮箱配置（优先从环境变量读取）
SMTP_SERVER = "smtp.qq.com"
SMTP_PORT = 465
SENDER_EMAIL = os.environ.get("SENDER_EMAIL", "REDACTED_SENDER_EMAIL")
SENDER_PASSWORD = os.environ.get("SENDER_PASSWORD", "REDACTED_QQ_AUTH_CODE   ")
RECEIVER_EMAIL = os.environ.get("RECEIVER_EMAIL", "REDACTED_SENDER_EMAIL")

# AI 配置（通义千问 Qwen）REDACTED_QWEN_API_KEY
QWEN_API_KEY = os.environ.get("QWEN_API_KEY", "REDACTED_QWEN_API_KEY")
QWEN_MODEL = "qwen-turbo"
QWEN_API_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions"

# 天气配置（高德地图天气 API）
WEATHER_API_KEY = os.environ.get("WEATHER_API_KEY", "")
WEATHER_API_URL = "https://restapi.amap.com/v3/weather/weatherInfo"
# 广州的 adcode
GUANGZHOU_ADCODE = "440100"

# ==================== 日志功能 ====================

def log_message(message):
    """打印并记录日志"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_line = f"[{timestamp}] {message}"
    print(log_line)
    with open("monitor.log", "a", encoding="utf-8") as f:
        f.write(log_line + "\n")

# ==================== 数据存储 ====================

def load_data():
    """加载历史监控数据"""
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            log_message(f"加载数据文件失败: {e}")
    return {"last_hash": "", "last_check": "", "articles": []}

def save_data(data):
    """保存监控数据"""
    try:
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        log_message(f"保存数据文件失败: {e}")

# ==================== 天气获取 ====================

def get_weather():
    """获取广州当前天气（高德地图API）"""
    if not WEATHER_API_KEY:
        log_message("未配置天气API Key，跳过天气获取")
        return None

    try:
        params = {
            "key": WEATHER_API_KEY,
            "city": GUANGZHOU_ADCODE,
            "extensions": "base",
            "output": "JSON"
        }
        response = requests.get(WEATHER_API_URL, params=params, timeout=10)
        if response.status_code == 200:
            data = response.json()
            if data.get("status") == "1" and data.get("lives"):
                live = data["lives"][0]
                weather_info = {
                    "temp": live.get("temperature", "未知"),
                    "weather": live.get("weather", "未知"),
                    "wind": live.get("winddirection", "未知") + live.get("windpower", ""),
                    "humidity": live.get("humidity", "未知"),
                    "city": live.get("city", "广州")
                }
                log_message(f"获取天气成功: {weather_info['weather']}, {weather_info['temp']}°C")
                return weather_info
            else:
                log_message(f"天气API返回错误: {data}")
        else:
            log_message(f"天气API请求失败，状态码: {response.status_code}")
    except Exception as e:
        log_message(f"获取天气异常: {e}")
    return None

# ==================== AI 问好生成 ====================

def generate_greeting(weather_info, hour):
    """根据时间和天气生成AI问好"""
    if not QWEN_API_KEY:
        # 无AI时简单生成
        if 5 <= hour < 12:
            period = "早上"
        elif 12 <= hour < 14:
            period = "中午"
        elif 14 <= hour < 18:
            period = "下午"
        else:
            period = "晚上"
        
        temp = weather_info.get("temp", "未知") if weather_info else "未知"
        return f"{period}好！现在温度{temp}度，祝你今天愉快！"
    
    # 构建提示词
    if 5 <= hour < 12:
        period = "早上"
    elif 12 <= hour < 14:
        period = "中午"
    elif 14 <= hour < 18:
        period = "下午"
    else:
        period = "晚上"
    
    weather_desc = ""
    if weather_info:
        weather_desc = f"当前天气: {weather_info.get('weather', '未知')}, 温度{weather_info.get('temp', '未知')}°C, 湿度{weather_info.get('humidity', '未知')}%, 风向风力: {weather_info.get('wind', '未知')}"
    else:
        weather_desc = "未获取到天气信息"
    
    prompt = f"现在是{period}，{weather_desc}。请用温暖亲切的语气写一句{period}问候语，包含温度和穿衣建议（冷了提醒多穿，热了提醒别中暑），控制在50字以内。只输出问候语本身，不要加任何前缀。"
    
    headers = {
        "Authorization": f"Bearer {QWEN_API_KEY}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "model": QWEN_MODEL,
        "messages": [
            {"role": "user", "content": prompt}
        ],
        "max_tokens": 100
    }
    
    try:
        log_message("正在生成AI问候语...")
        response = requests.post(QWEN_API_URL, headers=headers, json=payload, timeout=30)
        if response.status_code == 200:
            result = response.json()
            greeting = result["choices"][0]["message"]["content"].strip()
            log_message(f"AI问候语生成完成: {greeting[:30]}...")
            return greeting
        else:
            log_message(f"AI问候语生成失败: {response.status_code}")
    except Exception as e:
        log_message(f"AI问候语生成异常: {e}")
    
    # 失败时返回简单问候
    temp = weather_info.get("temp", "未知") if weather_info else "未知"
    return f"{period}好！现在温度{temp}度，祝你今天愉快！"

# ==================== 网页抓取 ====================

def fetch_page(url):
    """抓取网页内容"""
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        "Connection": "keep-alive",
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=30)
        response.encoding = 'utf-8'
        if response.status_code == 200:
            return response.text
        else:
            log_message(f"请求失败，状态码: {response.status_code}")
            return None
    except Exception as e:
        log_message(f"请求异常: {e}")
        return None

def parse_articles(html):
    """解析网页中的文章列表"""
    soup = BeautifulSoup(html, 'html.parser')
    articles = []

    li_items = soup.find_all('li', class_='no')
    for li in li_items:
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

            full_url = urljoin(MONITOR_URL, href)

            articles.append({
                "title": title,
                "url": full_url,
                "date": date_str,
                "summary": summary[:200] + "..." if len(summary) > 200 else summary
            })
        except Exception:
            continue

    return articles

def calculate_hash(content):
    """计算内容哈希值"""
    return hashlib.md5(content.encode('utf-8')).hexdigest()

def get_first_article(articles):
    """获取页面排列在最上面的文章"""
    if not articles:
        return None
    return articles[0]

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
            lines = [line.strip() for line in text.splitlines() if line.strip()]
            return '\n'.join(lines)
        else:
            body = soup.find('body')
            if body:
                text = body.get_text(separator='\n', strip=True)
                lines = [line.strip() for line in text.splitlines() if line.strip()]
                return '\n'.join(lines)
    except Exception as e:
        log_message(f'提取文章正文失败: {e}')
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
                "content": "你是一个专业的招生信息分析助手。请用简洁清晰的中文总结以下内容，提取关键信息（如重要时间节点、要求、变动等），控制在300字以内。"
            },
            {
                "role": "user",
                "content": f"请总结以下招生信息文章：\n\n{text}"
            }
        ]
    }
    
    try:
        log_message("正在调用AI总结文章...")
        response = requests.post(QWEN_API_URL, headers=headers, json=payload, timeout=60)
        if response.status_code == 200:
            result = response.json()
            summary = result["choices"][0]["message"]["content"]
            log_message("AI总结完成")
            return summary
        else:
            log_message(f"AI API请求失败，状态码: {response.status_code}")
            return f"（AI总结失败，原文如下）\n\n{text}"
    except Exception as e:
        log_message(f"AI总结异常: {e}")
        return f"（AI总结异常，原文如下）\n\n{text}"

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

# ==================== 主监控逻辑 ====================

def check_updates():
    """检查页面更新并发送邮件"""
    log_message("开始检查页面更新...")
    
    # 获取当前时间
    now = datetime.now()
    current_hour = now.hour
    
    # 获取天气
    weather_info = get_weather()
    
    # 生成AI问候语
    greeting = generate_greeting(weather_info, current_hour)
    
    # 加载历史数据
    data = load_data()
    
    # 获取当前页面内容
    html = fetch_page(MONITOR_URL)
    if not html:
        log_message("获取页面失败，跳过本次检查")
        # 即使页面获取失败，也发送问候邮件
        body = f"{greeting}\n\n{'='*40}\n\n（招生网页面获取失败，请稍后查看）"
        send_email("【招生网监控】每日问候", body)
        return
    
    # 解析文章列表
    current_articles = parse_articles(html)
    if not current_articles:
        log_message("未解析到文章列表")
        body = f"{greeting}\n\n{'='*40}\n\n（未能解析到文章列表）"
        send_email("【招生网监控】每日问候", body)
        return
    
    log_message(f"成功解析到 {len(current_articles)} 篇文章")
    
    # 计算当前文章列表的哈希
    articles_str = json.dumps(current_articles, sort_keys=True, ensure_ascii=False)
    current_hash = calculate_hash(articles_str)
    
    # 检查是否有更新
    has_update = False
    if data["last_hash"] == "":
        log_message("首次运行，初始化数据...")
    elif data["last_hash"] != current_hash:
        log_message("检测到页面更新！")
        has_update = True
    else:
        log_message("页面未更新")
    
    # 获取首条文章
    first_article = get_first_article(current_articles)
    
    if first_article:
        log_message(f"当前首条文章: {first_article['title']} ({first_article['date']})")
        
        # 抓取文章详情页正文
        article_text = fetch_article_html(first_article['url'])
        
        # 调用AI总结
        if article_text:
            ai_summary = ai_summarize(article_text)
        else:
            ai_summary = "（未能提取正文内容）"
        
        # 组装邮件正文
        body = f"{greeting}\n\n"
        body += f"{'='*40}\n"
        
        if has_update:
            body += "🎉 【页面有更新】\n"
        else:
            body += "📋 【当前最新文章】\n"
        
        body += f"{'='*40}\n"
        body += f"标题: {first_article['title']}\n"
        body += f"日期: {first_article['date']}\n"
        body += f"链接: {first_article['url']}\n"
        body += f"{'='*40}\n"
        body += "【AI总结】\n"
        body += f"{'='*40}\n"
        body += ai_summary
        body += f"\n{'='*40}\n"
        body += "【原文】\n"
        body += f"{'='*40}\n"
        if article_text:
            body += article_text
        else:
            body += "（未能提取正文内容）"
        
        subject = f"【招生网】{first_article['title'][:30]}..."
        send_email(subject, body)
    else:
        log_message("未获取到首条文章")
        body = f"{greeting}\n\n{'='*40}\n\n（未获取到文章信息）"
        send_email("【招生网监控】每日问候", body)
    
    # 保存数据
    data["last_hash"] = current_hash
    data["articles"] = current_articles
    data["last_check"] = now.isoformat()
    save_data(data)

def main():
    """主函数"""
    log_message("=" * 50)
    log_message("广东工业大学研究生招生网监控脚本启动")
    log_message(f"监控页面: {MONITOR_URL}")
    log_message("运行模式: 每日8:00/12:00/17:00定时执行")
    log_message("=" * 50)
    
    # 检查配置
    if not SENDER_EMAIL or not SENDER_PASSWORD:
        log_message("⚠️ 警告: 邮箱配置不完整！")
        return
    
    # 执行检查
    check_updates()

if __name__ == "__main__":
    main()
