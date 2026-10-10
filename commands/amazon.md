---
description: 亚马逊 Listing 全流程：输入产品信息 → 标题（字符规范）→ 五点描述 → 关键词与 Search Terms → Listing 评分 → 合规 checklist，一条龙输出。
argument-hint: [产品一句话] [--score]
---

# /lhg-amazon-listing:amazon —— Listing 全流程

用户输入在 `$ARGUMENTS` 中：`[产品一句话] [--score]`。

## 流程（全程按 skills/lhg-amz-* 方法论执行）

### 1. 输入澄清

产品信息缺失 → 问：产品是什么、核心参数（材质/容量/尺寸）、目标人群、差异化卖点。
`--score` 模式 → 用户直接给现有 Listing 文档，跳到第 5 步只做评分。

### 2. 标题（加载 lhg-amz-title）

按标题公式输出：品牌 + 核心关键词 + 关键参数 + 规格：
- ≤200 个字符；包含核心关键词；无重复词、无全大写
- **红线**：无促销用语（包邮/热卖/送礼佳品）、无论限词（最/第一）、无违禁宣称

### 3. 五点描述（加载 lhg-amz-bullets）

输出 5 条 bullet，每条讲 1 个卖点（材质/功能/场景/规格/售后）：
- 每条 ≤500 字符；有大写标题开头更佳
- 只写可验证的事实，不编造参数

### 4. 关键词（加载 lhg-amz-keywords）

输出核心关键词清单 + Search Terms：
- Search Terms ≤250 字节（UTF-8）；无重复词；与标题重叠率 ≤50%
- **红线**：不许出现 ASIN、竞品品牌词

### 5. 评分与合规（加载 lhg-amz-compliance）

- 跑 `python3 ${CLAUDE_PLUGIN_ROOT}/scripts/audit/amazon_audit.py --target <目录>`
- 按 lhg-amz-compliance 评分卡打分（标题/五点/关键词/图片/类目/描述六维）
- blocker（违禁词/标题违规/Search Terms 超限/含 ASIN）必须清零

### 6. 落盘

Listing 文档存为 `listing-YYYYMMDD.md`（含日期/版本），结构：
`## 标题 / ## 核心关键词 / ## 五点描述 / ## Search Terms / ## 图片 / ## 类目 / ## 产品描述`

## 硬规则

- 参数没有就不写，不许编造容量/材质/认证。
- 违禁词与标题促销用语是 blocker，见一条改一条，不接受豁免。
