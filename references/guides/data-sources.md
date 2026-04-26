# 数据源指南

> 如何获取可信数据，控制数据质量

---

## 数据源分类

| 类别 | 来源 | 可靠性 | 用途 |
|------|------|--------|------|
| **官方** | 东方财富、同花顺、交易所 | ⭐⭐⭐⭐⭐ | 行情、公告、财务 |
| **Iwencai** | 问财API | ⭐⭐⭐⭐⭐ | 选股、财务、研报、新闻 |
| **准官方** | Wind、Choice、彭博 | ⭐⭐⭐⭐⭐ | 机构数据 |
| **社区** | 淘股吧、微博V、雪球 | ⭐⭐⭐ | 情绪、观点 |
| **小众** | 股吧、论坛、消息群 | ⭐⭐ | 参考，慎用 |

---

## Iwencai数据源

### Iwencai技能清单（需安装）

| 技能 | 数据类型 |
|------|----------|
| market-data-query | 行情数据 |
| financial-data-query | 财务数据 |
| a-share-screener | A股选股 |
| sector-screener | 板块选股 |
| research-report-search | 研报搜索 |
| announcement-search | 公告搜索 |
| news-search | 新闻搜索 |
| macro-data-query | 宏观数据 |
| industry-data-query | 行业数据 |
| event-data-query | 事件数据 |
| basic-info-query | 基本资料 |
| index-data-query | 指数数据 |
| convertible-bond-screener | 可转债选股 |
| etf-screener | ETF选股 |
| fund-screener | 基金选股 |
| futures-options-data-query | 期货期权数据 |

### Iwencai环境变量

```bash
export IWENCAI_BASE_URL=https://openapi.iwencai.com
export IWENCAI_API_KEY=【你的API_KEY】
```

---

## 优先级规则

### 硬数据（必须用官方/Iwencai）

| 数据类型 | 首选 | 备选 |
|----------|------|------|
| 行情数据 | Iwencai(market-data-query) | AkShare + 东财 |
| 财务数据 | Iwencai(financial-data-query) | 公司公告 |
| 选股筛选 | Iwencai(a-share-screener) | AkShare |
| 研报新闻 | Iwencai(research-report-search/news-search) | 交易所 |
| 资金流向 | 东财Level2、大智慧 | AkShare |
| 龙虎榜 | 交易所官方 | Iwencai |

### 软数据（可参考社区）

| 数据类型 | 来源 |
|----------|------|
| 情绪热度 | 淘股吧热门 |
| 大V观点 | 雪球、微博（需交叉验证） |
| 消息传言 | 仅作提醒，不作依据 |

---

## 数据获取工具

| 工具 | 数据类型 | 优先级 |
|------|----------|--------|
| **Iwencai系列** | 行情/财务/选股/研报 | 首选 |
| `mx-data` | 行情、资金、指标 | 备选 |
| `akshare-stock` | 实时行情、财务 | 备选 |
| `mx-finance-search` | 公告、新闻搜索 | 补充 |
| `taoguba-hot` | 社区情绪热度 | 辅助 |

---

## 数据时效性要求

| 数据类型 | 接受时效 | 超时处理 |
|----------|----------|----------|
| 实时行情 | <5分钟 | 降级参考 |
| 今日成交 | <15分钟 | 降级参考 |
| 公告/新闻 | <24小时 | 标记时间戳 |
| 财务数据 | 最新一期 | 使用季报/年报 |
| 历史数据 | 无限制 | 可用 |

---

## 数据可信度校验

### 三重校验原则

1. **来源校验**：数据必须来自≥2个独立源
2. **逻辑校验**：数据之间逻辑一致（如涨幅≠收盘价-昨收）
3. **异常校验**：偏离历史均值>30%需复核

### 常见错误数据

| 错误类型 | 特征 | 处理 |
|----------|------|------|
| 停牌数据 | 成交量=0 | 剔除 |
| 复权错误 | 涨幅异常 | 使用前复权 |
| 单位错误 | 成交额亿/万混淆 | 统一单位 |
| 时区错误 | 夜盘数据混入 | 分开处理 |

---

## 数据使用规范

### ✅ 正确做法

- 优先使用 Iwencai + AkShare 双源
- 标注数据时间戳
- 发现异常数据主动提示用户

### ❌ 禁止做法

- 禁止使用单一来源作为交易依据
- 禁止使用超过时效的数据做决策
- 禁止传播未经核实的小道消息
