# 高PR选股

> 筛选高盈亏比（Risk/Reward）机会的标准化流程

## 三重过滤器

### Step 1：基本面+趋势+流动性筛选

使用 `mx-stocks-screener` 筛选：

```bash
python3 get_data.py \
  --query "股价在20日均线上方，成交额排名前50，市盈率<40的A股" \
  --select-type A股
```

> 高换手率确保趋势有资金支撑

### Step 2：技术数据提取

使用 `mx-finance-data` 提取技术位：

```bash
python3 get_data.py "查询 [股票代码] 最新股价、20日均线位置、BOLL轨道"
```

### Step 3：情报合成

使用 `mx-financial-assistant` 结合技术+催化剂：

```bash
python3 generate_answer.py \
  --query "分析 [个股] 高盈亏比机会。结合：1. [近期催化剂]；2. 业绩；3. 均线支撑。给出买入/目标/止损建议。" \
  --deep-think
```

## 选股标准

| 维度 | 标准 |
|------|------|
| 基本面 | PE<25（或行业平均），Q1/年增长>20% |
| 技术面 | 价格在20/60日均线的2-3%范围内 |
| 催化剂 | 明确上涨理由（政策/断供/同行带动） |
| 风险收益 | 目标收益 ≥ 3×止损距离 |

## R3红线过滤

```
安全⭐ < 3 → 不买
安全⭐ ≥ 3 + 机会⭐ ≥ 3 + 确定⭐ ≥ 3 → 可以买
```

> 参考：[references/core/rating/](references/core/rating/)
