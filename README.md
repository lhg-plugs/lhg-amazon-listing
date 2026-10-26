<!-- About 简介（推送后填写到仓库 About 栏）：
亚马逊卖家 Listing 方法论：标题/五点/关键词/评分/合规一条龙 ｜ 一键安装：/plugin marketplace add lhg-plugs/lhg-amazon-listing
-->
<!-- topics（推送后打）：claude-code, claude-plugin, agent-skills, amazon, ecommerce, seo -->

# lhg-amazon-listing：亚马逊运营专家

> **一句话介绍**：给 AI 助手装上"亚马逊 Listing 组合拳"——标题字符规范、五点描述、关键词与 Search Terms、Listing 六维评分、合规 checklist，16 条确定性规则自动体检，小白也能写出合规的 Listing。
>
> **一键安装**：在 Claude Code 里运行
> ```
> /plugin marketplace add lhg-plugs/lhg-amazon-listing
> /plugin install lhg-amazon-listing@lhg-plugs
> ```

## 它是什么

`lhg-amazon-listing` 是一个 Claude Code 插件（plugin 为主、skill 为辅）：

- **4 个命令**（小白入口）：`amazon` Listing 全流程一条龙，`keywords` 关键词挖掘与 Search Terms，`score` Listing 六维评分，`audit` 合规自查
- **4 个平台中立 skill**（方法论，可移植到豆包/Workbuddy 等 agent 平台）：标题规范、五点描述、关键词、合规与评分
- **2 个专家 agent**：Listing 撰写专家、Listing 审计专家
- **2 个硬门 hooks**：commit 前审计拦截（违禁词/标题违规/Search Terms 超限）、写 Listing 文档时标题超长/缺五点提醒（均可一键豁免）
- **16 条确定性审计规则**：纯 Python、零第三方依赖，秒级出结果

## 4 个命令用法

| 命令 | 作用 | 示例 |
|---|---|---|
| `/lhg-amazon-listing:amazon` | Listing 全流程：产品信息 → 标题 → 五点 → 关键词 → 评分 → 合规 | `/lhg-amazon-listing:amazon "316不锈钢保温杯 1000ml"` |
| `/lhg-amazon-listing:keywords` | 关键词挖掘：四类词 → Search Terms（≤250字节） | `/lhg-amazon-listing:keywords "保温杯"` |
| `/lhg-amazon-listing:score` | Listing 评分：脚本 + 六维评分卡，输出百分制与改进清单 | `/lhg-amazon-listing:score listing.md` |
| `/lhg-amazon-listing:audit` | 合规自查：脚本 + 人工复核，输出分级报告 | `/lhg-amazon-listing:audit` |

## 自查说明

自查 = 确定性脚本（机器）+ 人工复核清单（人）：

1. 先跑 `scripts/audit/amazon_audit.py`（16 条规则），零 LLM 成本；
2. 发现分三级：**blocker**（违禁词/标题促销用语/Search Terms 超 250 字节/含 ASIN，必须修，commit 前 hook 会拦截）、**warning**（标题超长/缺关键词/五点不足/图片不达标/类目缺失，修或写豁免理由）、**nit**（描述过短/缺日期版本，顺手修）；
3. 再按 `lhg-amz-compliance` 第 5 节人工复核清单过一遍脚本抓不到的（类目是否放对、违禁词变体、参数一致性）。

blocker 清零才算做完；为清零改规则算作弊，不许。

## 目录结构

```
lhg-amazon-listing/
├── .claude-plugin/          # plugin.json（插件清单）+ marketplace.json（本仓即市场）
├── commands/                # 4 个命令：amazon / keywords / score / audit
├── skills/                  # 4 个平台中立 skill（标题/五点/关键词/合规评分）
├── agents/                  # 2 个专家 agent（Listing 撰写专家 / Listing 审计专家）
├── hooks/                   # 2 个硬门（commit 前审计拦截 / Listing 文档提醒）+ 豁免说明
├── scripts/audit/           # 16 条确定性审计规则（零第三方依赖）
├── fixtures/                # 冒烟测试用例（坏/好对照）
├── smoke_test.py            # 一键冒烟测试
├── ATTRIBUTION.md           # 灵感来源与许可声明
└── LICENSE                  # MIT
```

## 什么时候用 / 什么时候不用（FAQ）

**什么时候用：**

- 你要上架亚马逊新品，标题/五点/Search Terms 无从下手 → 用 `/lhg-amazon-listing:amazon` 一条龙
- 你写完 Listing 心里没底，怕踩违禁词被下架 → 跑 `/lhg-amazon-listing:audit`，红线自动拦
- 你想知道现有 Listing 几分、从哪改起 → 用 `/lhg-amazon-listing:score`，六维打分 + 改进清单
- 你只想把 Search Terms 的 250 字节用满用准 → 用 `/lhg-amazon-listing:keywords`

**什么时候不用：**

- 你要的是自动上架、自动调价、ERP 对接 → 本插件只做 Listing 方法论与文档，不碰店铺操作
- 你的产品是特殊类目（医疗器械/食品/儿童用品），合规要求远超通用规则 → 通用违禁词表不够，需要叠加类目专项审核
- 你已经有成熟的 Listing SOP 和审稿流程 → 本插件的价值是"从 0 到 1 立规矩"，成熟团队用不上
- 你想让 AI 替你"保证上首页" → 排名是综合结果，本插件只保证 Listing 本身合规完整，不承诺排名

## lhg-plugs 插件矩阵

| 插件 | 一句话 | 安装 |
|---|---|---|
| [lhg-fullstack](https://github.com/lhg-plugs/lhg-fullstack) | 小白一句话 → 高质量全栈应用 | `/plugin install lhg-fullstack@lhg-plugs` |
| [lhg-amazon-listing](https://github.com/lhg-plugs/lhg-amazon-listing) | 亚马逊运营专家：标题/五点/关键词/评分/合规一条龙 | `/plugin install lhg-amazon-listing@lhg-plugs` |

## 自检与反馈

本插件自带质检：每次使用后可跑 `python3 smoke_test.py` 一键验证（JSON 合法、skill/command/agent 完整性、16 条规则、fixtures 命中、hooks 行为）。

发现 bug 或有改进建议，以 `[QC] <一句话问题>` 为标题提交到 https://github.com/lhg-plugs/lhg-amazon-listing/issues，正文写清"复现步骤 → 实际表现 → 期望表现"。

## 出品：刘洪光

本插件由真人出镜 IP「刘洪光」（安徽合肥）出品，归属 [lhg-skills](https://github.com/lhg-skills)。

- GitHub 主页：https://github.com/lhg-skills —— 全部 skill 开源在此，欢迎 star
- 抖音：搜「刘老师讲AI实战」
- 微信：lhgsmsw
