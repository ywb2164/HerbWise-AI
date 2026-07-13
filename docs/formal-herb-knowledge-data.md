# 45 类中药材结构化知识数据

## 1. 文件说明

数据文件：

```text
data/knowledge/herb_profiles.v1.json.gz
```

导入脚本：

```text
backend/scripts/import_herb_knowledge.py
```

该数据集与以下模型类别映射保持一一对应：

```text
data/models/medicine-class-mapping.csv
```

共包含 45 个训练类别。每个药材至少包含：

- 标准中文名
- 标准英文名
- 模型训练类别名
- 拉丁药名
- 常见别名
- 基原与药用部位
- 常见产区
- 外观性状
- 断面特征
- 质地
- 气味与滋味
- 炮制或商品形态
- 质量关注点
- 易混淆与风险提示

同时提供部分高频易混淆药材对，用于教学和识别结果复核。

## 2. 数据状态

当前数据状态为：

```text
curated_draft_needs_professional_review
```

这表示数据已经过结构化整理，可以用于：

- 系统开发
- 图片识别结果说明
- 教学演示
- 质控实训
- RAG 查询构造
- 相似药材对比卡生成

但仍不应标记为：

- 药典全文数据
- 已通过药师终审的数据
- 临床诊断依据
- 处方或用药建议
- 医疗生产环境中的最终质控结论

正式比赛展示前，建议由中药学教师、中药师或药典资料负责人逐条复核，并将 `knowledge_sources.review_status` 更新为正式审核状态。

## 3. 来源和版权边界

数据集记录了以下来源类型：

1. 《中华人民共和国药典》2020 年版一部的书目级参考；
2. 香港浸会大学中医药学院中药材图像数据库；
3. HerbWise-AI 项目整理的识别与易混淆提示。

仓库不保存或分发《中国药典》全文，也不批量复制外部数据库原文。数据文件中的性状描述为面向识别教学的压缩和改写字段。

## 4. 导入方法

Docker 环境中先进行校验：

```powershell
docker compose -f compose.yaml -f compose.dev.yaml exec -T api `
  uv run python scripts/import_herb_knowledge.py `
  /data/knowledge/herb_profiles.v1.json.gz `
  --dry-run
```

正式导入：

```powershell
docker compose -f compose.yaml -f compose.dev.yaml exec -T api `
  uv run python scripts/import_herb_knowledge.py `
  /data/knowledge/herb_profiles.v1.json.gz
```

脚本会幂等地更新：

- `knowledge_sources`
- `medicine_items`
- `medicine_aliases`
- `medicine_features`
- `similar_medicines`

对于导入范围内的药材，脚本默认删除完全匹配以下内容的演示特征：

```text
feature_name = demo_feature
feature_value = demo_seed_data
```

需要保留演示特征时使用：

```powershell
--keep-demo
```

需要导出可读 JSON 供人工审阅时执行：

```powershell
docker compose -f compose.yaml -f compose.dev.yaml exec -T api `
  uv run python scripts/import_herb_knowledge.py `
  /data/knowledge/herb_profiles.v1.json.gz `
  --export-json /data/knowledge/herb_profiles.v1.review.json
```

## 5. 数据校验

运行专用测试：

```powershell
docker compose -f compose.yaml -f compose.dev.yaml exec -T api `
  uv run pytest tests/test_herb_knowledge_dataset.py -q
```

测试会检查：

- 数据集恰好包含 45 类；
- 与模型类别映射完全一致；
- 中文名、类别名和内部代码无重复；
- 每味药均具备必要的鉴别与质控字段；
- 相似药材关系没有悬空引用。

## 6. 特殊类别说明

### 去皮桃仁

`Peeled Peach Kernel` 对应去皮桃仁，是桃仁的加工商品形态，不是独立物种。数据库保留独立训练类别，是为了兼容现有视觉模型；标准化和报告中必须显示它与桃仁的加工关系。

### 川贝母

`Fritillaria` 在模型类别映射中对应川贝母。贝母类来源和商品规格复杂，模型输出只应作为候选结果。高风险场景应结合规格、来源凭证和人工复核。

### 木通

木通类药材历史名称和来源较复杂。系统应优先依赖数据库中的标准来源和批次信息，不得只依据通用名称推断药材来源。

### 冬虫夏草

冬虫夏草价格高、伪品和加工增重风险较高。单张图片识别不能替代来源审查和人工鉴定，系统应默认保留风险提示。
