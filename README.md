# A股散户盈利助手

一个面向 Agent 的 A 股分析 Skill，目标是默认使用最新在线可信数据，输出稳定的 `诊股 / 选股 / 风控 / 盘前盘后复盘 / 市场周期判断 / 方法论执行手册 / 交易计划 / 新闻 / 公告 / 资金流 / 行业轮动 / 热点强势股 / 概念板块 / 研报 / 龙虎榜 / 融资融券 / 大宗交易 / 股东户数 / 分红 / 解禁 / 北向资金 / 个股信息 / 批量实时行情 / K线 / 五档盘口 / 逐笔成交 / 季报快照 / F10 公司资料 / 财报三表 / 一致预期 / 估值 / 批量对比 / 主题研报批量检索 / 快速调研 / iwencai 语义检索` 结果。

## 当前改造方向

- 统一入口：所有能力收敛到 `scripts/run_skill.py`
- 全栈在线数据：腾讯行情 + 东财新闻/研报/资金流/行业/龙虎榜/两融/大宗/股东户数/分红/解禁 + 财联社快讯 + 同花顺北向/一致预期/热点强势股/概念题材 + mootdx K线 / 五档盘口 / 逐笔成交 / 季报快照 / F10 文本资料 + 新浪财报三表 + 可选 iwencai 语义检索
- 工作流产品化：`valuation`、`quick-research`、`theme-research` 统一输出 `workflow / generated_at / input / degraded / errors / coverage / summary`
- 方法论落地：新增 `market-cycle` 和 `playbook`，把市场阶段、仓位节奏、入场/加仓/减仓/离场规则和纪律约束显式化
- 健康检查增强：`self-check` 现在会输出依赖状态、凭证状态、关键能力检查和推荐动作
- 兼容 Agent：`SKILL.md` 采用 OpenClaw / Hermes 都能消费的元数据形式
- 可测试：仓库内置自检和测试脚本

## 核心工作流

- `valuation`
  单票完整估值，聚合实时行情和一致预期，输出前向 PE、PEG、PE 消化年数。
- `quick-research`
  新标的快速调研，聚合估值、概念、资金流、龙虎榜、解禁、两融、股东户数和近端研报。
- `theme-research`
  主题研报批量检索，支持多 query `iwencai` 语义检索和东财研报补充。

## OpenClaw 自然语言使用

这个 Skill 的目标用法不是让最终用户手写命令，而是让 OpenClaw 在后台根据自然语言自动选择工作流并执行命令。

- 用户说 `宁德时代能买吗`
  OpenClaw 应路由到 `diagnose`，必要时补 `playbook`
- 用户说 `今天市场情绪怎么样，适合进攻还是防守`
  OpenClaw 应路由到 `market-cycle`
- 用户说 `帮我快速研究一下比亚迪`
  OpenClaw 应路由到 `quick-research`
- 用户说 `机器人主题最近有什么研报`
  OpenClaw 应路由到 `theme-research`

当前 CLI 也已支持 `股票代码或简称`，因此即使 OpenClaw 把 `宁德时代` 直接作为参数传入，skill 也会在内部解析成对应股票代码。

## 快速开始

```bash
pip install .
a-shares-skill self-check
a-shares-skill valuation --code 300750
a-shares-skill quick-research --code 300750 --date 2026-05-29
a-shares-skill theme-research --queries "人形机器人产业链深度 2026,人形机器人减速器 丝杠" --channel report --size 5 --supplement-per-stock 2

# 仓库内开发模式
python3 scripts/run_skill.py self-check
python3 scripts/run_skill.py risk --code 300750
python3 scripts/run_skill.py diagnose --code 300750 --date 2026-05-28
python3 scripts/run_skill.py pick --filters basic,tech,catalyst
python3 scripts/run_skill.py market-cycle --date 2026-05-28
python3 scripts/run_skill.py plan --code 300750 --date 2026-05-28
python3 scripts/run_skill.py playbook --code 300750 --date 2026-05-28
python3 scripts/run_skill.py news --code 300750 --page-size 3
python3 scripts/run_skill.py announcements --code 300750 --page-size 3
python3 scripts/run_skill.py fund-flow --code 300750 --period minute
python3 scripts/run_skill.py sectors --top 5
python3 scripts/run_skill.py hot-stocks --page-size 5
python3 scripts/run_skill.py concept-blocks --code 300750
python3 scripts/run_skill.py reports --code 300750 --page-size 3
python3 scripts/run_skill.py dragon-tiger --code 002428 --date 2026-05-28
python3 scripts/run_skill.py daily-dragon-tiger --date 2026-05-28 --min-net-buy 5000
python3 scripts/run_skill.py margin --code 300750 --page-size 3
python3 scripts/run_skill.py block-trades --code 300750 --page-size 3
python3 scripts/run_skill.py holders --code 300750 --page-size 3
python3 scripts/run_skill.py dividends --code 300750 --page-size 3
python3 scripts/run_skill.py lockup --code 002428 --date 2026-05-28 --forward-days 90
python3 scripts/run_skill.py northbound --history-days 5
python3 scripts/run_skill.py stock-info --code 300750
python3 scripts/run_skill.py quotes --codes 300750,sh000300,510300 --kind auto
python3 scripts/run_skill.py valuation --code 300750
python3 scripts/run_skill.py compare --codes 300750,002594
python3 scripts/run_skill.py theme-research --queries "人形机器人产业链深度 2026,人形机器人减速器 丝杠" --channel report --size 5 --supplement-per-stock 2
python3 scripts/run_skill.py quick-research --code 300750 --date 2026-05-29
python3 scripts/run_skill.py kline --code 300750 --frequency 4 --limit 5
python3 scripts/run_skill.py order-book --code 300750
python3 scripts/run_skill.py transactions --code 300750 --start 0 --limit 5
python3 scripts/run_skill.py quarterly-snapshot --code 300750
python3 scripts/run_skill.py f10 --code 300750 --category 最新提示
python3 scripts/run_skill.py finance --code 300750 --report-type lrb --page-size 1
python3 scripts/run_skill.py consensus-eps --code 300750
python3 scripts/run_skill.py iwencai-search --query "人形机器人 行星滚柱丝杠 2026" --channel report --size 3
sh scripts/run_tests.sh
```

## 安装层级

- 基础版：`pip install .`
  适合使用默认在线数据层和统一 CLI。
- `mootdx` 增强版：`pip install .[mootdx]`
  增加 `quarterly-snapshot`、`f10`、`kline`、`order-book`、`transactions` 等能力的真数据支持。
- 开发版：`pip install .[dev]`
  包含 `mootdx` 和测试依赖，适合本地开发和回归。
- `iwencai` 增强层：无需额外 pip 包，但需要设置 `IWENCAI_API_KEY`
  启用 `iwencai-search`、`iwencai-query`、`theme-research` 的在线语义检索。

## 配置

- 默认在线模式：见 `.env.example`
- 安装后默认命令名：`a-shares-skill`
- 开发模式也支持：`python3 -m src.main ...`
- 若要启用 `quarterly-snapshot` / `f10` 真数据，请安装可选依赖：`pip install .[mootdx]`
- 若要本地开发并跑测试，推荐：`pip install .[dev]`
- `iwencai` 检索需要显式配置 `IWENCAI_API_KEY`
- `theme-research` 依赖 `iwencai` 检索能力，因此在线模式下同样需要 `IWENCAI_API_KEY`
- 自定义本地样本数据：设置 `A_SHARE_SKILL_DATA_PATH=/path/to/data.json`
- 离线模式只建议用于测试或上游行情不可达时排障

## 目录

```text
src/
  config/      统一配置
  core/        分析 / 评级 / 风控 / 工作流
  modules/     盘前、盘后、选股、交易计划
  providers/   在线优先数据层（腾讯 / 东财 / 同花顺 / mootdx / 巨潮 / 财联社）
  skill.py     单一 Skill 入口
scripts/
  run_skill.py 统一 CLI
  run_tests.sh 测试入口
tests/
  skills/      技能兼容性和行为测试
```

## 说明

当前版本已经把默认路径切到在线可信多源数据；离线 fixture 仅保留给测试和受限环境。
