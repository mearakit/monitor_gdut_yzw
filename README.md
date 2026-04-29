# 广东工业大学研究生招生网监控

[![Monitor](https://github.com/mearakit/monitor_gdut_yzw/actions/workflows/monitor.yml/badge.svg)](https://github.com/mearakit/monitor_gdut_yzw/actions/workflows/monitor.yml)

> 自动监控广东工业大学研究生招生网（yzw.gdut.edu.cn）最新文章，定时发送邮件通知。

## 功能特性

- **定时监控**：每天北京时间 8:00、12:00、17:00 自动检查
- **AI 智能总结**：使用通义千问 API 对文章进行智能摘要
- **天气问候**：获取实时天气，生成温暖的问候语
- **邮件推送**：通过 QQ 邮箱推送最新招生信息

## 项目结构

```
.
├── .github/
│   └── workflows/
│       └── monitor.yml      # GitHub Actions 定时任务配置
├── monitor_gdut_yzw.py      # 主监控脚本
├── .env                     # 本地环境变量（已删除，不要提交到仓库）
└── README.md                # 本文件
```

## 快速开始

### 1. Fork 本仓库

点击右上角 **Fork** 按钮，将仓库复制到你的账号下。

### 2. 配置 Secrets

进入你 Fork 的仓库 → **Settings** → **Secrets and variables** → **Actions** → **New repository secret**，添加以下 5 个 Secrets：

| Secret 名称 | 说明 | 获取方式 |
|------------|------|---------|
| `SENDER_EMAIL` | 发件人 QQ 邮箱 | 你的 QQ 邮箱地址 |
| `SENDER_PASSWORD` | QQ 邮箱授权码 | [QQ 邮箱设置 → 账户 → 开启 SMTP](https://mail.qq.com) |
| `RECEIVER_EMAIL` | 收件人邮箱 | 接收通知的邮箱地址 |
| `QWEN_API_KEY` | 通义千问 API 密钥 | [阿里云 DashScope](https://dashscope.aliyun.com/) |
| `WEATHER_API_KEY` | 高德地图 API 密钥 | [高德开放平台](https://lbs.amap.com/) |

### 3. 手动测试

进入仓库 → **Actions** → **GDUT YZW Monitor** → **Run workflow**，点击运行测试是否能收到邮件。

### 4. 完成

GitHub Actions 会按照设定的时间自动运行，无需额外操作。

## 本地运行

如果你想在本地运行或调试：

```bash
# 克隆仓库
git clone https://github.com/你的用户名/monitor_gdut_yzw.git
cd monitor_gdut_yzw

# 安装依赖
pip install requests beautifulsoup4 python-dotenv

# 设置环境变量（Windows PowerShell）
$env:SENDER_EMAIL="你的QQ邮箱"
$env:SENDER_PASSWORD="邮箱授权码"
$env:RECEIVER_EMAIL="接收邮箱"
$env:QWEN_API_KEY="通义千问API密钥"
$env:WEATHER_API_KEY="高德API密钥"

# 运行脚本
python monitor_gdut_yzw.py
```

## 定时配置

默认每天运行 3 次（北京时间）：

| 时间 | 说明 |
|------|------|
| 08:00 | 早上问候 + 最新文章 |
| 12:00 | 中午问候 + 最新文章 |
| 17:00 | 晚上问候 + 最新文章 |

如需修改，请编辑 `.github/workflows/monitor.yml` 中的 `cron` 表达式。

## 技术栈

- **Python 3.11**
- **requests** - HTTP 请求
- **BeautifulSoup4** - HTML 解析
- **GitHub Actions** - 定时任务调度
- **通义千问 API** - AI 文本总结
- **高德天气 API** - 实时天气获取

## 监控目标

- 网址：https://yzw.gdut.edu.cn/sszs.htm
- 内容：广东工业大学研究生招生最新动态

## 注意事项

1. **不要**将 `.env` 文件或任何包含密钥的文件提交到仓库
2. QQ 邮箱授权码不是登录密码，需要在邮箱设置中单独开启 SMTP 获取
3. 免费版通义千问 API 有调用额度限制

## 许可证

MIT License

## 致谢

- 广东工业大学研究生招生网
- 阿里云通义千问
- 高德地图开放平台
