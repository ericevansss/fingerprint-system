# 指纹识别分析系统（FastAPI + FingerNet + Qt）

本项目是一个用于毕业设计展示的指纹识别与脊线分析系统，后端基于 FastAPI + PyTorch + OpenCV，前端使用 Qt（PySide6）构建桌面应用。

## 功能亮点

- 指纹图像上传与解析
- 预处理流程（CLAHE、Gabor 增强、前景分割）
- FingerNet 风格多头模型输出（方向场、分割、增强、细节点）
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
    fingernet.pth
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
- `weights/fingernet.pth` 可替换为你训练好的 FingerNet 权重。
- 目前是 FingerNet 风格架构，若已有真实 FingerNet，可继续替换模型内部结构。
