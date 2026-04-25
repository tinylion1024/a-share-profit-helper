# 文档索引

> A股散户盈利助手完整文档索引

---

## 核心文档

| 文件 | 内容 | 路径 |
|------|------|------|
| **[SKILL.md](../SKILL.md)** | 主索引，极简入口 | SKILL.md |
| **[core/rating/](core/rating/)** | 四维评级体系 | references/core/rating/ |
| **[core/four-dimensions.md](core/four-dimensions.md)** | 三维市场分析 | references/core/ |
| **[guides/rules.md](guides/rules.md)** | 七条硬规则 | references/guides/ |
| **[guides/scenes.md](guides/scenes.md)** | 15场景体系 | references/guides/ |
| **[core/tgb-sentiment.md](core/tgb-sentiment.md)** | TGB情绪分析 | references/core/ |
| **[core/feedback-loop.md](core/feedback-loop.md)** | 反馈循环 | references/core/ |

---

## 交易指南

| 文件 | 内容 | 路径 |
|------|------|------|
| **[guides/anchors.md](guides/anchors.md)** | 买卖锚点、仓位模型、止损原则 | references/guides/ |
| **[guides/templates.md](guides/templates.md)** | 操作/学习/进化报告模板 | references/guides/ |
| **[guides/pitfalls.md](guides/pitfalls.md)** | 散户亏损反模式清单 | references/guides/ |

---

## 目录结构

```
a-shares-master/
├── SKILL.md                    # 主索引（极简）
├── config.json                 # 用户配置（自动生成）
├── config.json.example         # 配置模板
├── README.md                   # 项目说明
│
├── references/
│   ├── index.md               # 本索引页
│   ├── install.md             # 安装指南
│   ├── CHANGELOG.md           # 变更日志
│   │
│   ├── core/                  # 核心体系
│   │   ├── rating/            # 四维评级（机会/安全/确定/舒适）
│   │   │   ├── README.md
│   │   │   ├── opportunity.md
│   │   │   ├── safety.md
│   │   │   ├── certainty.md
│   │   │   └── comfort.md
│   │   ├── four-dimensions.md # 三维市场分析
│   │   ├── tgb-sentiment.md  # TGB情绪分析
│   │   └── feedback-loop.md  # 反馈循环
│   │
│   ├── guides/                # 操作指南
│   │   ├── rules.md          # 七条硬规则
│   │   ├── anchors.md        # 买卖锚点
│   │   ├── scenes.md         # 15场景体系
│   │   ├── templates.md      # 报告模板
│   │   └── pitfalls.md       # 反模式避坑
│   │
│   └── workflows/             # 工作流
│       ├── pre-market.md
│       ├── post-market.md
│       ├── high-pr-picker.md
│       ├── trading-plan.md
│       └── market-synthesis.md
│
├── scripts/                    # 执行脚本
│   ├── config_manager.py      # 配置管理
│   ├── check_risk.py          # 风控扫描
│   ├── pre_market.py          # 盘前分析
│   ├── post_market.py         # 盘后复盘
│   ├── stock_picker.py        # 选股
│   ├── trading_plan.py        # 交易计划
│   └── market_analysis.py     # 市场分析
│
└── src/                       # 源代码
    ├── __init__.py
    ├── config/
    ├── core/
    ├── modules/
    ├── plugins/
    └── utils/
```

---

## 按任务索引

| 任务 | 查阅文档 |
|------|---------|
| **了解系统** | SKILL.md |
| **安装配置** | references/install.md |
| **理解评级** | references/core/rating/ |
| **分析股票** | references/core/four-dimensions.md |
| **TGB情绪** | references/core/tgb-sentiment.md |
| **选股** | references/guides/scenes.md, workflows/high-pr-picker.md |
| **诊股** | references/guides/scenes.md, references/guides/anchors.md |
| **风控扫描** | references/guides/rules.md, scripts/check_risk.py |
| **制定交易计划** | scripts/trading_plan.py, references/guides/anchors.md |
| **盘前分析** | scripts/pre_market.py, workflows/pre-market.md |
| **盘后复盘** | scripts/post_market.py, workflows/post-market.md |
| **写报告** | references/guides/templates.md |
| **避免错误** | references/guides/pitfalls.md |
| **持续进化** | references/core/feedback-loop.md |

---

## 快速命令

```bash
# 配置向导
python3 scripts/config_manager.py

# 风控扫描
python3 scripts/check_risk.py --code 300750

# 盘前分析
python3 scripts/pre_market.py --date 2024-01-15

# 盘后复盘
python3 scripts/post_market.py --date 2024-01-15

# 选股
python3 scripts/stock_picker.py --filters basic,tech,catalyst

# 交易计划
python3 scripts/trading_plan.py --stock 300750
```

---

## 版本信息

- Skill Version: 1.0
- Last Updated: 2024-04-25
- 详见 [CHANGELOG.md](CHANGELOG.md)
