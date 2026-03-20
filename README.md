# 指纹识别分析系统（FastAPI + ResNet-18 + Qt）

本项目是一个用于毕业设计展示的指纹识别与脊线分析系统，后端基于 FastAPI + PyTorch + OpenCV，前端使用 Qt（PySide6）构建桌面应用。

## 功能亮点

- 指纹图像上传与解析
- 预处理流程（CLAHE、Gabor 增强、前景分割）
- ResNet-18 指纹类型分类（arch / left_loop / right_loop / whorl）
- 脊线计数（骨架化 + 中心线统计）与密度估计
- 可选返回增强图、骨架图、脊线图，支持可视化展示

## 目录结构

```
fingerprint-system/
  app/
    api/
      routes.py
    models/
      fingernet_model.py
    schemas/
      response_schema.py
    services/
      preprocessing.py
      fingernet_service.py
      ridge_count_service.py
      result_fusion.py
    utils/
      image_utils.py
      file_utils.py
    config.py
    main.py
  external/
    ridge_counting/
  weights/
    resnet18_fingerprint.pth
  frontend/
    main.py
    requirements.txt
    ui/
      Main.qml
  requirements.txt
  README.md
```

## 后端运行

1. 创建并激活 Python 3.10 环境（或使用你的 conda 环境）
2. 安装依赖：

```bash
pip install -r requirements.txt
```

3. 启动服务：

```bash
uvicorn app.main:app --reload
```

服务地址：`http://127.0.0.1:8000`

## API 调用示例

### POST /analyze

- Content-Type: `multipart/form-data`
- 字段：`file`（指纹图像）
- 可选参数：`return_images=true` 返回增强图/骨架图/脊线图

```bash
curl -X POST \
  -F "file=@/path/to/fingerprint.jpg" \
  "http://127.0.0.1:8000/analyze?return_images=true"
```

返回示例：

```json
{
  "fingerprint_type": "whorl",
  "confidence": 0.92,
  "ridge_count": 17,
  "ridge_density": 0.18,
  "minutiae_points": [
    {"x": 120, "y": 80, "score": 0.87, "angle": 45.0}
  ],
  "processing_time": "0.38s",
  "enhanced_image": "<base64>",
  "skeleton_image": "<base64>",
  "ridge_map_image": "<base64>"
}
```

## 前端运行（Qt）

进入 `frontend` 目录并安装依赖：

```bash
cd frontend
pip install -r requirements.txt
```

运行桌面端：

```bash
python main.py
```

前端将自动调用本地 `http://127.0.0.1:8000/analyze?return_images=true` 接口。

## 说明

- 模型只会在后端启动时加载一次。
- 当前分类模型为 ResNet-18，权重文件：`weights/resnet18_fingerprint.pth`。
- 方向场/骨架/细节点/脊线计数由传统算法模块提供，与分类模型解耦。

## ResNet-18 训练与评估（SD04）
最新评估结果（SD04，4 类，T 归并为 arch，img_size=192）：

- Accuracy: **0.9865**
- Confusion matrix:
```
[[1586   12    2    0]
 [  10  787    0    3]
 [  22    0  777    1]
 [   0    1    3  796]]
```

完整训练流程见 `training_log.md`。
