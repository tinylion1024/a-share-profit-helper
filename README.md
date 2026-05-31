# A股散户盈利助手

一个面向 Agent 的 A 股研究与交易分析 Skill。

它的目标不是做“单一数据接口封装”，而是把行情、资金、公告、研报、社区情绪、方法论规则、用户偏好与记忆，收敛成一套统一入口，直接输出可执行的市场判断和单票结论。

当前项目已经更接近一套：

- 题材周期 + 情绪博弈 + 龙头/中军交易的规则化研究系统
- 面向 OpenClaw / Hermes / Claude Code 的 A 股分析 Skill
- 在线优先、离线可测、可持续积累用户记忆的研究工具

## 项目定位

这个项目主要解决 4 类问题：

1. 今天市场是进攻、试仓还是防守？
2. 这只股票能买吗，风险大不大，应该怎么执行？
3. 这个题材最近有没有持续强化，市场和社区在看什么？
4. 我最近反复研究过哪些股票和题材，系统能不能记住并不断演化？

它不是纯价值投资模型，也不是纯量化埋伏系统。

当前主风格是：

- 题材周期
- 情绪博弈
- 龙头 / 中军识别
- 纪律化执行
- 基本面与研报作为辅助验证

## 当前核心特性

### 1. 统一 Skill 入口

所有能力统一收敛到：

- 安装后命令：`a-shares-skill`
- 仓库内入口：`python3 scripts/run_skill.py`
- 模块入口：`python3 -m src.main`

核心封装在 [src/skill.py](/Users/zhangshaowei/Documents/Codex/2026-05-28/tinylion1024-a-share-profit-helper-https/repo/src/skill.py)。

### 2. 在线优先的多源数据层

当前已经接入的主要数据面包括：

- 腾讯财经：实时报价、批量 quotes
- 东方财富：新闻、公告、研报、资金流、行业板块、龙虎榜、两融、大宗、股东户数、分红、解禁
- 同花顺：热点强势股、概念题材、北向资金、一致预期
- 淘股吧：热点帖子、市场舆情、个股情绪、大 V 观点
- 财联社：快讯
- `mootdx`：K 线、五档盘口、逐笔成交、季报快照、F10
- 新浪：财报三表
- `iwencai`：语义检索与主题研究

### 3. 对外主打能力已经收敛

现在对外最主打的不是几十个命令，而是 6 条旗舰工作流：

- `market-cycle`：今天是进攻、试仓还是防守
- `leaders`：全市场主线、龙头、中军、补涨梯队扫描
- `diagnose`：这只票能不能做
- `playbook`：这只票应该怎么执行
- `quick-research`：快速研究一个新标的
- `theme-research`：围绕一个题材做批量研究

其它命令继续保留，但更适合看成这 6 条旗舰流程的底层能力。

### 4. 社区情绪层

项目已经显式支持淘股吧信号，并融入交易体系：

- `taoguba-hot`
- `taoguba-sentiment`
- `taoguba-stock`
- `taoguba-vip`

这些能力已经进入：

- `market-cycle`
- `diagnose`
- `quick-research`

### 5. 时间感知

Skill 已有统一时间上下文层，会根据盘前、盘中、盘后、周末、历史回看，自动选择合适的数据窗口和证据范围，而不是简单把“今天”硬塞给所有流程。

### 6. 用户偏好与进化记忆

当前项目已经支持用户画像和持续演化记忆：

- 偏好：风险偏好、默认周期、偏好板块、回避板块、自选股、偏好风格
- 记忆：最近看过的股票、最近跑过的工作流、单票笔记
- 股票画像：风格、setup、社区情绪、题材标签、催化、方法论评分均值
- 题材画像：关联股票、近期理由、热度来源、阶段分布

对应命令：

- `profile-show`
- `profile-set`
- `memory-show`
- `memory-note`
- `memory-clear`

### 7. 复盘闭环

现在已经不是“看完就结束”，而是有完整复盘闭环：

- `review-trade`：记录单笔交易结果
- `weekly-review`：汇总最近一段时间的交易表现
- `memory-feedback`：把复盘结果转成下一阶段的行动建议

这会把复盘结果反写成：

- setup 胜率
- 风格胜率
- 板块/题材收益偏好
- 股票层经验统计

## 最推荐的使用方式

如果你只想记住一条主线，建议按这个顺序使用：

1. 先看市场环境
2. 再扫主线和龙头
3. 再看单票值不值得做
4. 最后看执行和研究补充
5. 交易后做复盘和反馈

对应命令：

```bash
a-shares-skill market-cycle
a-shares-skill leaders
a-shares-skill diagnose --code 宁德时代
a-shares-skill playbook --code 宁德时代
a-shares-skill quick-research --code 宁德时代
a-shares-skill review-trade --code 宁德时代 --outcome win --return-pct 8.5 --holding-days 3 --theme 储能
a-shares-skill weekly-review --limit 10
a-shares-skill memory-feedback --limit 10
```

## 快速开始

### 安装

基础版：

```bash
pip install .
```

带 `mootdx` 的增强版：

```bash
pip install .[mootdx]
```

开发和测试：

```bash
pip install .[dev]
```

### 自检

```bash
a-shares-skill self-check
```

仓库内开发模式：

```bash
python3 scripts/run_skill.py self-check
```

### 常见环境变量

- `A_SHARE_SKILL_OFFLINE_MODE=true`
  仅用于测试或排障，强制使用离线 fixture
- `A_SHARE_SKILL_DATA_PATH=/path/to/data.json`
  指定离线样本数据
- `IWENCAI_API_KEY=...`
  启用在线 `iwencai` 检索与 `theme-research`

## Show Case

### Case 1：盘前先看今天适合进攻还是防守

```bash
a-shares-skill market-cycle
a-shares-skill leaders
a-shares-skill pre-market
```

适合回答：

- 当前是加速、试探还是退潮
- 总仓位上限大概多少
- 更适合主攻、试仓还是防守
- 热点在哪，情绪锚点是谁
- 今天主线板块和龙头是谁

### Case 2：我有一只票，想知道能不能买

```bash
a-shares-skill diagnose --code 宁德时代
a-shares-skill playbook --code 宁德时代
```

适合回答：

- 这只票是主线龙头、趋势中军还是观察股
- 适合分歧低吸还是趋势跟随
- 买点、加仓点、减仓点、离场条件是什么

### Case 3：我想快速研究一个标的

```bash
a-shares-skill quick-research --code 寒武纪
```

输出会聚合：

- 估值
- 概念题材
- 资金流
- 龙虎榜 / 两融 / 股东户数 / 解禁
- 研报与公告
- 淘股吧情绪和大 V 观点
- 方法论层的市场阶段与风格判断

### Case 4：我想看题材，不是看单票

```bash
a-shares-skill theme-research --queries 机器人,储能 --channel report --size 5 --supplement-per-stock 2
```

适合回答：

- 某个主题最近有哪些研报
- 有哪些标的被反复提及
- 哪些题材正在强化

### Case 5：我想单独观察社区情绪

```bash
a-shares-skill taoguba-sentiment --page-size 10
a-shares-skill taoguba-stock --code 宁德时代 --page-size 20
a-shares-skill taoguba-vip --code 宁德时代 --page-size 10
```

适合回答：

- 淘股吧最近最热在聊什么
- 某只票股民整体偏多还是偏空
- 有没有大 V 在持续关注

### Case 6：我希望系统记住我反复关注的票和题材

```bash
a-shares-skill profile-set --risk-preference 稳健型 --default-horizon 波段 --preferred-sectors 储能,机器人 --watchlist 宁德时代,比亚迪
a-shares-skill quick-research --code 宁德时代
a-shares-skill theme-research --queries 机器人,储能 --channel report --size 3 --supplement-per-stock 1
a-shares-skill memory-show --code 宁德时代
a-shares-skill profile-show
```

这套流程会让系统逐步沉淀：

- 你偏好的题材和风格
- 最近反复研究的股票
- 单票画像和题材画像
- 题材和股票之间的关联关系

### Case 7：我想把交易结果真正沉淀成经验

```bash
a-shares-skill quick-research --code 宁德时代
a-shares-skill review-trade --code 宁德时代 --outcome win --return-pct 9.5 --holding-days 3 --theme 储能 --note 分歧低吸后延续
a-shares-skill weekly-review --limit 10
a-shares-skill memory-feedback --limit 10
```

适合回答：

- 最近哪些 setup 胜率高
- 哪种风格最容易亏钱
- 哪些题材最值得继续跟踪
- 下一阶段应该收缩什么、强化什么

## 常用命令分组

### 核心交易工作流

- `market-cycle`
- `leaders`
- `diagnose`
- `risk`
- `pick`
- `plan`
- `playbook`
- `pre-market`
- `post-market`

### 研究工作流

- `quick-research`
- `theme-research`
- `valuation`
- `compare`

### 社区情绪

- `taoguba-hot`
- `taoguba-sentiment`
- `taoguba-stock`
- `taoguba-vip`

### 新闻与事件

- `news`
- `telegraph`
- `global-news`
- `announcements`
- `reports`

### 资金与筹码

- `fund-flow`
- `dragon-tiger`
- `daily-dragon-tiger`
- `margin`
- `block-trades`
- `holders`
- `dividends`
- `lockup`
- `northbound`

### 行情与基础资料

- `quotes`
- `stock-info`
- `concept-blocks`
- `sectors`
- `hot-stocks`
- `kline`
- `order-book`
- `transactions`
- `quarterly-snapshot`
- `f10`
- `finance`
- `consensus-eps`

### 用户画像与记忆

- `flagship`
- `profile-show`
- `profile-set`
- `memory-show`
- `memory-note`
- `memory-clear`
- `review-trade`
- `weekly-review`
- `memory-feedback`

## OpenClaw / Hermes / Claude Code 使用说明

这个项目的目标用法，不是让最终用户背命令，而是让 Agent 在后台自动路由。

自然语言和命令的推荐映射：

- “今天市场情绪怎么样，适合进攻还是防守？”
  - `market-cycle`
- “今天主线和龙头是谁？”
  - `leaders`
- “宁德时代能买吗？”
  - `diagnose`
- “给我宁德时代的买卖执行手册”
  - `playbook`
- “帮我快速研究一下比亚迪”
  - `quick-research`
- “机器人主题最近有什么研报和标的？”
  - `theme-research`
- “帮我做一下最近交易复盘，看看我到底适合什么 setup？”
  - `weekly-review`
- “根据最近复盘结果，给我下一阶段建议”
  - `memory-feedback`
- “淘股吧今天最热在聊什么？”
  - `taoguba-sentiment`
- “宁德时代在淘股吧上的情绪怎么样？”
  - `taoguba-stock`

当前 CLI 已支持“股票代码或简称”两种输入方式。

例如下面这些都可以：

```bash
a-shares-skill diagnose --code 300750
a-shares-skill diagnose --code 宁德时代
a-shares-skill quick-research --code 比亚迪
```

## 目录结构

```text
src/
  config/        配置
  core/          方法论、分析、风控、时间上下文
  modules/       盘前、盘后、选股、交易计划
  providers/     在线数据层与离线 fixture
  utils/         通用工具
  skill.py       统一 Skill facade
  main.py        安装型 CLI 入口
  cli.py         文本渲染
  user_context.py 用户偏好与进化记忆
scripts/
  run_skill.py   仓库内兼容入口
  run_tests.sh   测试入口
tests/
  skills/        兼容性与行为测试
```

## 验证与测试

运行自检：

```bash
a-shares-skill self-check
python3 -m src.main self-check
```

运行测试：

```bash
sh scripts/run_tests.sh
```

如果安装了 `pytest`，也可以：

```bash
python3 -m pytest -q tests
```

## 当前边界

- 默认契约是在线可信数据，离线模式只建议用于测试或排障
- 社区情绪目前重点接在淘股吧，东方财富股吧还没有完整并入
- 这是研究与分析 Skill，不是自动交易系统
- 估值、情绪、方法论和社区信号会辅助决策，但不应被理解为收益承诺

## 一句话总结

如果你把它当成“一个会看市场环境、会看单票、会看题材、会看社区情绪、还能记住你长期关注方向并持续进化的 A 股 Agent Skill”，这个理解是准确的。
