# YOLO 药材模型目录

将项目专用的 45 类中药饮片 YOLO 权重放在此目录：

```text
data/models/herbwise-yolo26s.pt   # 修正类别名称元数据后的运行权重，本地放置
data/models/medicine-class-mapping.csv # 45 类模型到药材知识库的名称映射
```

运行权重大小约 19.5 MiB，SHA256：

```text
BCC439F4D43A38A7445265779F328697FE197A8627C6E861042A969786498EBA
```

Docker Compose 会把本机的 `./data` 挂载到 API 容器的 `/data`，因此拿到权重后在
`backend/.env` 中使用以下配置：

```env
LOCAL_VISION_ENABLED=true
LOCAL_MODEL_TYPE=ultralytics
LOCAL_MODEL_PATH=/data/models/herbwise-yolo26s.pt
LOCAL_MODEL_DEVICE=auto
LOCAL_MODEL_IMAGE_SIZE=960
LOCAL_MODEL_CONFIDENCE_THRESHOLD=0.10
```

注意：

- 当前 `yolo26s.pt` 是 45 类中药材检测权重，不是普通 COCO 权重。
- 原始权重把每个类别名称错误保存成了字典字符串；运行副本只修正类别名称元数据，不修改网络参数。
- 模型类别名称应与药材知识库可归一化的名称一致。
- `ultralytics` 已在后端依赖中声明，执行 `uv sync` 或重新构建 API 镜像时会自动安装。
- 所有 `.pt` 权重均不提交 Git；本目录只提交说明文件和类别映射 CSV。

首次配置数据库时，导入模型类别映射：

```powershell
docker compose exec -T api uv run python scripts/import_medicine_class_mapping.py `
  /data/models/medicine-class-mapping.csv
```

配置完成后可在 API 容器中检查：

```powershell
docker compose exec api uv run python scripts/local_model_doctor.py --info
docker compose exec api uv run python scripts/local_model_doctor.py --load
```
