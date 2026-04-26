# 公共SOP 1：澄清用户需求

> 每个场景开始前，必须先澄清用户真实需求

---

## 目的

避免误判，确保分析的股票/问题和用户想要的匹配。

---

## 操作步骤

### Step 1：识别场景类型

用户需要的是哪种场景？

| 场景大类 | 场景细分 | 对应SOP |
|----------|----------|---------|
| **赚钱** | 不知道买什么 | [stock-picker.md](../make-money/stock-picker.md) |
| **赚钱** | 纠结买不买 | [stock-diagnosis.md](../make-money/stock-diagnosis.md) |
| **赚钱** | 纠结卖不卖 | [position-diagnosis.md](../make-money/position-diagnosis.md) |
| **赚钱** | 被套了 | [unstuck.md](../make-money/unstuck.md) |
| **赚钱** | 亏多少必须走 | [stop-loss.md](../make-money/stop-loss.md) |
| **赚钱** | 赚多少要跑 | [take-profit.md](../make-money/take-profit.md) |
| **学习** | 今天怎么看 | [market-outlook.md](../learn/market-outlook.md) |
| **学习** | 为什么涨/跌 | [market-summary.md](../learn/market-summary.md) |
| **学习** | 操作对吗 | [daily-review.md](../learn/daily-review.md) |
| **学习** | 为什么涨/跌 | [case-analysis.md](../learn/case-analysis.md) |
| **学习** | 为什么亏 | [error-reflection.md](../learn/error-reflection.md) |
| **学习** | 怎么赚到的 | [experience.md](../learn/experience.md) |
| **进化** | 记录这笔 | [case-record.md](../evolve/case-record.md) |
| **进化** | 更新规则 | [rule-update.md](../evolve/rule-update.md) |
| **进化** | 调整参数 | [model-tune.md](../evolve/model-tune.md) |

### Step 2：确认必要信息

根据场景类型，确认需要的信息：

| 场景 | 必须确认 |
|------|----------|
| 选股/诊股 | 股票代码 |
| 持仓诊断/解套 | 股票代码 + 成本价 |
| 止损/止盈 | 股票代码 + 买入价 |
| 大盘分析 | 时间（今日/指定日期） |
| 复盘 | 日期 + 操作记录 |

### Step 3：确认用户意图

- 用户的真实问题是什么？
- 用户期望得到什么？
- 用户当前处境（空仓/轻仓/重仓）？

---

## 输出

```markdown
【需求澄清】
场景类型：XXX
股票代码：XXX（如适用）
必要信息：已确认/缺失
用户意图：XXX
```

---

## 常见错误

| 错误 | 后果 |
|------|------|
| 用户说"帮我看看"但没说股票 | 必须追问代码 |
| 用户说"被套了"但没说成本 | 必须追问 |
| 用户问"能买吗"但没说持仓周期 | 必须追问 |

---

## 关联SOP

- 公共SOP 2：[02-define-time-window.md](02-define-time-window.md)
- 公共SOP 3：[03-get-data.md](03-get-data.md)
