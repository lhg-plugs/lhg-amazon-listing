---
description: Listing 合规自查：跑确定性审计脚本（违禁词/标题/关键词/图片/类目），输出分级报告并修复 blocker。
argument-hint: [文档目录] [--fix]
---

# /lhg-amazon-listing:audit —— 合规自查

用户输入在 `$ARGUMENTS` 中：`[文档目录] [--fix]`。目录缺省为当前项目根目录。

## 流程（加载 lhg-amz-compliance 第 4 节人工复核清单配合）

### 1. 跑脚本

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/audit/amazon_audit.py --target <目录> --format text
```

记下 blocker / warning / nit 的数量与明细（含文件、行号、规则说明）。

### 2. 分级与修复

- blocker（违禁词 AMZ-VIO-001、标题违规 AMZ-VIO-002、Search Terms 超限 AMZ-KW-001、含 ASIN AMZ-KW-004）：逐条修，`--fix` 缺省即自动修（删除/改写问题表述）；**不接受豁免**。
- warning（标题/五点/关键词/图片/类目）：修掉或写豁免理由。
- nit（描述过短/缺日期版本）：顺手修。
- **为清零改脚本规则或阈值 → 作弊，不许。**

### 3. 人工复核

按 lhg-amz-compliance 第 4 节清单执行脚本抓不到的：
- 类目是否放对（机器只能检查"有没有声明"，对不对要人看）
- 违禁词变体：拼音/谐音/拆字绕过（如"治愈"写成"治愈力"也算）
- 参数真实性：标题与五点里的参数是否一致、有无编造

### 4. 输出报告

输出分级自查报告，结论写清"通过 / 不通过"（有 blocker 即不通过）。

## 硬规则

- 有 blocker 就说"通过" → 不许。
- 违禁词类 blocker 不接受豁免，只能删除。
