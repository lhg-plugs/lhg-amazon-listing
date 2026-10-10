---
description: Listing 评分：对现有 Listing 文档跑确定性审计 + 六维人工评分卡，输出百分制评分与改进清单。
argument-hint: [Listing 文档路径]
---

# /lhg-amazon-listing:score —— Listing 评分

用户输入在 `$ARGUMENTS` 中：`[Listing 文档路径]`（缺省为当前目录下的 listing 文档）。

## 流程（加载 lhg-amz-compliance 评分卡）

### 1. 跑脚本（必做）

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/audit/amazon_audit.py --target <目录> --format text
```

记下 blocker / warning / nit 明细。

### 2. 六维打分

按 lhg-amz-compliance 第 3 节评分卡打分（每维 0-100）：

| 维度 | 权重 | 看什么 |
|---|---|---|
| 标题 | 25% | 字符规范、核心关键词、合规 |
| 五点描述 | 25% | 5 条齐全、每条一卖点、无超长 |
| 关键词 | 20% | Search Terms 字节/重复/重叠/ASIN |
| 图片 | 15% | ≥6 张、尺寸 ≥2000px |
| 类目 | 5% | 类目声明、节点合理性（人工判） |
| 产品描述 | 10% | ≥200 字、补充信息 |

### 3. 输出

- 总分（加权）+ 定级：90+ 优秀 / 75-89 良好 / 60-74 待改进 / 60 以下重写
- **改进清单**：按"blocker → 高权重维度 → 低权重维度"排序，每条写清改法
- 有 blocker 时总分直接判"不通过"，不许给高分

## 硬规则

- 评分只基于文档呈现的内容，不许脑补"图片应该不错"。
- 为高分改规则或阈值 → 作弊，不许。
