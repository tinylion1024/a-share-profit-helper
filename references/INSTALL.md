# 安装指南

## 环境要求

- Python 3.8+
- Node.js 16+（部分依赖需要）
- 网络能访问东方财富、淘股吧等国内站点

---

## 依赖 Skill 安装

### 自动安装

在 Claude Code 中使用 `/install` 命令安装：

```bash
/install mx-stocks-screener
/install mx-finance-data
/install mx-financial-assistant
/install mx-finance-search
/install mx-data
/install taoguba-hot
/install akshare-stock
/install open-gstack-browser
```

### 手动安装

将 skill 克隆到 `~/.claude/skills/` 目录：

```bash
# 创建目录
mkdir -p ~/.claude/skills

# 克隆各依赖 skill（以 mx-stocks-screener 为例）
git clone https://github.com/tinylion1024/mx-stocks-screener.git ~/.claude/skills/mx-stocks-screener

# 其他依赖同理...
```

---

## 环境变量配置

### 1. 获取 API 密钥

| 服务 | 获取地址 | 说明 |
|------|---------|------|
| MX API | https://mx.com | 量化数据 API |
| EM API | https://eastmoney.com | 东方财富 API |

### 2. 配置环境变量

```bash
# 方式一：复制配置模板
cp .env.example .env

# 方式二：手动设置
export MX_APIKEY="your_mx_apikey_here"
export EM_API_KEY="your_em_apikey_here"
```

### .env.example 文件内容

```bash
# MX API 密钥（必需）
MX_APIKEY=your_mx_apikey_here

# EM API 密钥（必需）
EM_API_KEY=your_em_apikey_here

# 数据缓存目录（可选）
DATA_CACHE_DIR=/tmp/a_shares_cache

# 日志级别（可选，默认 INFO）
LOG_LEVEL=INFO
```

---

## 用户配置

首次运行时会自动启动配置向导，询问用户偏好并生成 `config.json`：

```bash
# 自动触发（首次运行任意脚本）
python3 scripts/check_risk.py --code 300750

# 或手动运行配置向导
python3 scripts/config_manager.py
```

### 配置项说明

| 类别 | 配置项 | 说明 |
|------|--------|------|
| **用户** | 昵称/经验级别 | 个性化标识 |
| **账户** | 总资金 | 计算仓位用 |
| **交易** | 单只仓位/总仓位/止损/止盈 | 交易参数 |
| **筛选** | 最小成交额/股价范围 | 股票筛选条件 |
| **展示** | 概率/风险/推理显示 | 输出偏好 |

### 配置文件位置

```
config.json          # 用户配置（自动生成，git忽略）
config.json.example  # 配置模板（git版本控制）
```

---

## 依赖检查

安装完成后，验证所有依赖是否就绪：

```bash
for skill in mx-stocks-screener mx-finance-data mx-financial-assistant mx-finance-search mx-data taoguba-hot akshare-stock open-gstack-browser; do
  if [ -d "$HOME/.claude/skills/$skill" ]; then
    echo "✅ $skill"
  else
    echo "❌ $skill - 未安装"
  fi
done
```

期望输出：

```
✅ mx-stocks-screener
✅ mx-finance-data
✅ mx-financial-assistant
✅ mx-finance-search
✅ mx-data
✅ taoguba-hot
✅ akshare-stock
✅ open-gstack-browser
```

---

## Python 依赖安装

部分脚本需要额外的 Python 包：

```bash
pip install pandas akshare requests
```

或使用 requirements.txt：

```bash
pip install -r requirements.txt
```

---

## 常见问题

### Q: 安装命令无效？

确保 Claude Code 版本支持 `/install` 命令，或手动克隆 skill。

### Q: API 密钥在哪里获取？

访问对应服务的官网注册账号并申请 API 密钥。

### Q: 浏览器工具无法使用？

确保已安装 `open-gstack-browser`，并配置好浏览器驱动。

### Q: 报错 "No module named 'akshare'"？

执行 `pip install akshare` 安装 Python 依赖。

---

## 验证安装

安装完成后，测试核心脚本：

```bash
# 测试风控扫描
python3 scripts/check_risk.py --code 300750

# 测试市场分析
python3 scripts/market_analysis.py
```

无报错即安装成功。
