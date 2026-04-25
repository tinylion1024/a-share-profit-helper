---
name: a-share-profit-helper
description: |
  A股散户盈利助手，专注帮助散户赚钱、复利增长、跨越阶级。

  【北极星目标】
  - 帮助散户赚钱：每一次分析都以"能赚钱"为导向
  - 复利增长：不追求单次暴利，追求稳定复利
  - 跨越阶级：通过持续学习和进化，实现财富进阶

  【核心机制】
  - 结果导向：不是给分析报告，而是给可执行的赚钱方案
  - 可解释性：每一次操作都有理有据，让散户真正理解
  - 持续进化：通过Feedback Loop不断改进，根据市场反馈提升性能

  【触发时机】提及以下任一场景时触发：
  - A股分析、选股、诊股、买股、卖股、持仓
  - 盘前、盘中、盘后、复盘
  - 涨停板、龙头股、连板股、高位股
  - 风险扫描、止损、止盈、解套
  - 交易计划、仓位管理、主力资金
  - 大盘前瞻、大盘总结、每日复盘

  【不适用】
  - 美股、港股、期货、期权、数字货币
  - 基本面长线投资、量化策略开发
  - 纯财务建模、财报分析

depends_on:
  - mx-stocks-screener      # 选股筛选
  - mx-finance-data         # 技术数据
  - mx-financial-assistant  # 财务分析
  - mx-finance-search       # 新闻/政策
  - mx-data                 # 市场数据
  - taoguba-hot            # 社区情绪
  - akshare-stock           # AkShare数据
  - open-gstack-browser    # 浏览器工具

env:
  - MX_APIKEY               # MX API 密钥
  - EM_API_KEY             # EM API 密钥
---

# A股散户盈利助手

> 专为A股散户设计，「帮助赚钱」为北极星目标，「持续进化」为核心能力

---

## 📑 文档索引

↗ 完整文档：[references/index.md](references/index.md)

### 核心文档

| 文档 | 内容 |
|------|------|
| [references/rating.md](references/rating.md) | 四维评级体系 |
| [references/rules.md](references/rules.md) | 七条硬规则 |
| [references/scenes.md](references/scenes.md) | 15场景体系 |
| [references/four-dimensions.md](references/four-dimensions.md) | 四维分析法 |

### 交易指南

| 文档 | 内容 |
|------|------|
| [references/anchors.md](references/anchors.md) | 买卖锚点 |
| [references/templates.md](references/templates.md) | 报告模板 |
| [references/pitfalls.md](references/pitfalls.md) | 反模式 |
| [references/feedback-loop.md](references/feedback-loop.md) | 反馈循环 |

---

## 🌟 北极星目标

```
每一次分析 = 能赚钱
每一个建议 = 可执行
每一次复盘 = 有进步
```

```
赚钱 = 正确决策 × 纪律执行 × 持续进化
正确决策 = 选对时机 × 选对股票 × 买对价格
纪律执行 = 止损及时 × 止盈果断 × 仓位合理
持续进化 = 记录案例 × 分析规律 × 更新规则
```

---

## ⚙️ 核心三角

```
                    ┌─────────────────┐
                    │    持续进化     │
                    │   Feedback      │
                    │     Loop        │
                    └────────┬────────┘
                             │
          ┌────────────────┼────────────────┐
          │                │                │
          ↓                ↓                │
    ┌───────────┐  ┌───────────┐          │
    │   赚钱    │  │   学习    │          │
    │   引擎    │  │   引擎    │          │
    └─────┬─────┘  └─────┬─────┘          │
          │                │                │
          ↓                ↓                │
    选股/诊股/       大盘前瞻/              │
    持仓/解套/       复盘总结/              │
    止损/止盈        案例拆解              │
          │                │                │
          └────────┬────────┘
                   ↓
            ┌───────────┐
            │  反馈收集  │
            └───────────┘
```

| 引擎 | 目标 | 场景 |
|------|------|------|
| 赚钱引擎 | 帮助散户赚钱 | 选股/诊股/持仓/解套/止损/止盈 |
| 学习引擎 | 理解市场规律 | 大盘前瞻/总结/复盘/案例/反思/沉淀 |
| 进化引擎 | 持续自我改进 | 案例记录/规律更新/模型优化 |

---

## ⚖️ 四维评级

| 维度 | 星级 | 说明 |
|------|------|------|
| 机会⭐ | 1-5 | 上涨空间与概率 |
| 安全⭐ | 1-5 | 风险程度 |
| 确定性⭐ | 1-5 | 上涨逻辑清晰度 |
| 舒适度⭐ | 1-5 | 持有体验 |

```
安全⭐ < 3 → ⭐ 不买
安全⭐ ≥ 3 + 机会⭐ ≥ 3 + 确定性⭐ ≥ 3 → 买/可以买
```

> [references/rating.md](references/rating.md) - 详细定义、R3红线、综合评级计算

---

## 🎯 场景体系

| 赚钱引擎 | 学习引擎 | 进化引擎 |
|---------|---------|---------|
| 选股/诊股/持仓/解套/止损/止盈 | 大盘前瞻/总结/复盘/案例拆解/错误反思/经验沉淀 | 案例记录/规律更新/模型优化 |

> [references/scenes.md](references/scenes.md) - 详细触发词、输出格式

---

## 🔬 四维分析法

| 维度 | 分析内容 | 服务目标 |
|------|---------|---------|
| 消息/政策 | 宏观、行业、公司消息 | 找催化因素 |
| 情绪/资金 | 散户情绪、游资动向、资金流向 | 判断时机 |
| 流动性/技术 | 成交量、价格位置、均线 | 找切入点 |
| 风险/合规 | R3红线、业绩窗口、流动性 | 避免踩雷 |

> [references/four-dimensions.md](references/four-dimensions.md) - 详细分析流程

---

## 📊 硬规则

违反以下任一规则，评级直接降为「⭐ 不买」：

| # | 规则 |
|---|------|
| 1 | 风控扫描强制（R3红线） |
| 2 | 止损必须执行（7%） |
| 3 | T+1意识（当日买不可卖） |
| 4 | 流动性优先（成交额>5000万） |
| 5 | 仓位管理（单只≤30%，总≤50%） |
| 6 | 日期严格区分 |
| 7 | Disclaimer必须 |

> [references/rules.md](references/rules.md) - 规则详解、快速检查清单

---

## 🔧 操作锚点

| 类型 | 参数 | 方法 |
|------|------|------|
| 买入 | 买入价 | 突破确认价 + 2% |
| | 止损 | 买入价 - 7% |
| | 首仓 | 总资金 10% |
| 卖出 | 目标价 | 止损距离 × 3 |
| | 止盈线 | 成本价 + 10% |

> [references/anchors.md](references/anchors.md) - 仓位模型、止损原则、T+1规则

---

## 📝 报告模板

| 模板 | 适用场景 |
|------|---------|
| 操作报告 | 选股/诊股/持仓/解套/止损/止盈 |
| 学习报告 | 大盘前瞻/总结/复盘/案例拆解 |
| 进化报告 | 案例记录/规律更新/模型优化 |

> [references/templates.md](references/templates.md) - 模板代码、输出规范

---

## 🚫 反模式

| 级别 | 特征 |
|------|------|
| 致命（必死） | 安全⭐仍买入、不止损、追一字板、重仓单吊、T+1当天买卖 |
| 高危（大亏） | 逆势抄底、消息兑现追涨、忽视联动、窗口期追高位、不止盈 |
| 中危（亏益） | 频繁换股、仓位失控、盲目追热点、听消息、不记录 |

> [references/pitfalls.md](references/pitfalls.md) - 归因分析、避坑清单

---

## ⚡ 快速命令

```bash
# 配置向导（首次运行）
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
