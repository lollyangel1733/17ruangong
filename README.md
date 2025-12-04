# 金属幕墙锈蚀检测项目（Rust_detection）

本项目用于在前端页面中对上传的图像进行锈蚀检测与(可选)实例分割，并输出标注图与统计指标。后端基于 Flask + Ultralytics YOLO，支持使用内置检测模型(`yolo11n.pt`/`yolo11s.pt`)或训练得到的分割/检测权重（位于 `runs/*/weights/best.pt`）。

## 项目结构

- `app.py`：Web 服务入口（Flask）。提供模型列表接口与检测接口，渲染前端页面。
- `templates/index.html`：前端页面，支持图片上传、模型选择、参数配置(`conf`、`iou`、`imgsz`、`max_det`)与结果展示。
- `web_data/`：本地对象存储目录（模拟,本地运行后会生成）。
  - `uploads/`：保存上传的原始图片。
  - `outputs/`：保存检测后的标注图（按模型子目录归档）。
  - `results.csv`：检测记录与统计指标（时间戳、图片尺寸、检测数量、面积比例、平均置信度、参数）。
- `runs/`：训练输出目录（Ultralytics 默认结构），其中 `runs/<run_name>/weights/best.pt` 为最佳权重；前端会自动发现并展示可选用。
- `datasets/`：训练数据集（YOLO 标注格式）。
- `datasets_noRust/`：无锈蚀负样本集合（图片与占位标签）。
- `datasets_preprocessed/`、`datasets_preprocessed_v2/`：数据预处理后的数据集合。
- `preprocess.py` / `preprocess_config.yaml`：数据预处理脚本与配置（如 CLAHE、降噪、颜色空间转换等）。
- `train.py`：训练入口脚本（基于 Ultralytics YOLO）。
- `scripts/download_unsplash_no_rust.py`：负样本批量下载脚本（Unsplash），支持去重与按数量精确下载。（当时用于爬 `datasets_noRust数据集的`)
- `yolo11n.pt` / `yolo11s.pt`：内置检测模型权重。

## 环境依赖

- Python 3.9+（建议）
- 依赖包：`flask`、`ultralytics`、`torch`、`opencv-python`、`numpy`
- 安装示例：
  - `pip install flask ultralytics torch opencv-python numpy`

如使用 GPU，请确保对应版本的 `torch` 已正确安装（可参考 PyTorch 官方安装指引）。

## 运行服务

- 在项目根目录执行：
  - `python app.py`
- 默认启动在 `http://127.0.0.1:8000/`
- 页面使用方法：
  - 上传图片（支持常见格式）。
  - 选择模型：
    - 内置检测：`yolo11n.pt` 或 `yolo11s.pt`
    - 自训练权重：自动发现 `runs/<run_name>/weights/best.pt` 并在下拉列表显示。
  - 配置参数：`conf`（置信度阈值）、`iou`（NMS IoU 阈值）、`imgsz`（推理尺寸）、`max_det`（最大检测数量）。
  - 提交后返回：标注图（带框/分割可视化）、检测数量、面积比例、平均置信度；并自动保存到 `web_data/` 目录。

### 统计说明

- 检测数量：当前图像中检测到的实例总数。
- 面积比例：
  - 若模型为分割版（结果包含 `masks`），采用“掩膜并集面积比例”。
  - 否则采用“检测框并集面积比例”。
- 平均置信度：本次检测所有实例的平均 `conf`。

## 接口（后端 API）

- `GET /models`：返回可用模型列表。
- `GET /`：返回前端页面。
- `POST /detect`：执行检测。
  - 表单字段：
    - `file`：上传的图像文件。
    - `model`：模型键或路径（如 `yolo11s.pt` 或 `runs/rust_seg_v2/weights/best.pt`）。
    - `conf`：置信度阈值（默认 `0.25`）。
    - `iou`：NMS IoU 阈值（默认 `0.45`）。
    - `imgsz`：推理尺寸（默认 `640`）。
    - `max_det`：最大检测数量（默认 `300`）。
  - 返回 JSON：
    - `image_base64`：标注结果图（PNG）
    - `metrics`：`检测数量`、`面积比例`、`平均置信度`
    - `saved`：`original_path`、`output_path`

## 训练与数据

- 训练：
  - 参考 `train.py`（Ultralytics YOLO）。
  - 数据集配置一般为 `datasets/data.yaml`（包含 `train/valid/test` 路径和类别定义）。
  - 建议命令（示例，实际参数视你需求与 `train.py` 实现而定）：
    - `python train.py --data datasets/data.yaml --model yolov8n-seg.yaml --epochs 100 --imgsz 640`
- 数据预处理：
  - 使用 `preprocess.py` 配合 `preprocess_config.yaml` 批量处理训练图像。
  - 运行示例（查看帮助）：
    - `python preprocess.py -h`
      - 标注图：保存到 `web_data/outputs/<模型子目录>/..._detected.png`
