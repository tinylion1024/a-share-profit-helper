# 文档索引

> A股散户盈利助手完整文档索引

---

## 核心文档

| 文件 | 内容 | 行数 |
|------|------|------|
| **[SKILL.md](../SKILL.md)** | 主索引，极简入口 | ~150 |
| **[references/rating/](rating/)** | 四维评级体系 | 机会/安全/确定性/舒适度 |
| **[references/rules.md](rules.md)** | 七条硬规则 | ~150 |
| **[references/scenes.md](scenes.md)** | 15场景体系 | ~150 |
| **[references/four-dimensions.md](four-dimensions.md)** | 四维分析法 | ~200 |

---

## 交易指南

| 文件 | 内容 |
|------|------|
| **[references/anchors.md](anchors.md)** | 买卖锚点、仓位模型、止损原则 |
| **[references/templates.md](templates.md)** | 操作/学习/进化报告模板 |
| **[references/pitfalls.md](pitfalls.md)** | 散户亏损反模式清单 |
| **[references/feedback-loop.md](feedback-loop.md)** | 反馈循环与进化机制 |
| **[references/tgb-sentiment.md](tgb-sentiment.md)** | TGB情绪分析、大V观点整合 |

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
│   ├── INSTALL.md             # 安装指南
│   ├── rating.md              # 四维评级体系
│   ├── rules.md               # 硬规则
│   ├── scenes.md              # 场景体系
│   ├── four-dimensions.md     # 四维分析法
│   ├── anchors.md             # 操作锚点
│   ├── templates.md           # 报告模板
│   ├── pitfalls.md            # 反模式
│   ├── feedback-loop.md      # 反馈循环
│   ├── tgb-sentiment.md      # TGB情绪分析
│   │
│   ├── guides/                # 架构指南
│   │   ├── ARCHITECTURE.md
│   │   ├── MODULE_GUIDE.md
│   │   └── PLUGIN_GUIDE.md
│   │
│   ├── workflows/             # 工作流
│   │   ├── pre-market.md
│   │   ├── post-market.md
│   │   ├── high-pr-picker.md
│   │   ├── trading-plan.md
│   │   └── market-synthesis.md
│   │
│   ├── trading/               # 交易相关
│   │   ├── basic-strategies.md
│   │   ├── money-management.md
│   │   ├── sentiment-analysis.md
│   │   ├── a-share-rules.md
│   │   ├── pitfalls.md
│   │   └── industry-codes.md
│   │
│   └── cases/                 # 案例库
│       ├── 成功案例/
│       ├── 失败案例/
│       └── 市场规律/
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
| **安装配置** | references/INSTALL.md |
| **理解评级** | references/rating.md |
| **分析股票** | references/four-dimensions.md |
| **TGB情绪** | references/tgb-sentiment.md |
| **选股** | references/scenes.md, workflows/high-pr-picker.md |
| **诊股** | references/scenes.md, references/anchors.md |
| **风控扫描** | references/rules.md, scripts/check_risk.py |
| **制定交易计划** | scripts/trading_plan.py, references/anchors.md |
| **盘前分析** | scripts/pre_market.py, workflows/pre-market.md |
| **盘后复盘** | scripts/post_market.py, workflows/post-market.md |
| **写报告** | references/templates.md |
| **避免错误** | references/pitfalls.md |
| **持续进化** | references/feedback-loop.md |

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
