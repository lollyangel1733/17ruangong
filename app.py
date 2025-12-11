import os
import io
import base64
import time
import uuid
import csv
from typing import Dict, Tuple
import threading
import queue

from flask import Flask, request, jsonify, render_template
# 惰性导入YOLO，避免服务启动阶段因缺少依赖而失败
try:
    from ultralytics import YOLO  # 如果存在则直接使用
except Exception:
    YOLO = None
import numpy as np
import cv2

# Flask app
app = Flask(__name__, template_folder=os.path.join(os.path.dirname(__file__), 'templates'))
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024  # 单请求最大50MB

# Model cache to avoid reloading every request
_loaded_models: Dict[str, object] = {}
_jobs_lock = threading.Lock()
_jobs: Dict[str, Dict] = {}
_job_queue: "queue.Queue" = queue.Queue(maxsize=100)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MODEL_FILES = {
    'yolo11s.pt': os.path.join(BASE_DIR, 'yolo11s.pt'),
    'yolo11n.pt': os.path.join(BASE_DIR, 'yolo11n.pt'),
}

# 发现runs目录中的自定义训练权重（best.pt）
def discover_models() -> Dict[str, str]:
    discovered: Dict[str, str] = {}
    runs_dir = os.path.join(BASE_DIR, 'runs')
    if os.path.isdir(runs_dir):
        for root, dirs, files in os.walk(runs_dir):
            # 仅关注weights目录中的best.pt
            if os.path.basename(root) == 'weights' and 'best.pt' in files:
                rel = os.path.relpath(os.path.join(root, 'best.pt'), BASE_DIR)
                key = rel.replace('\\', '/')  # 统一为/分隔，便于前端使用
                discovered[key] = os.path.join(BASE_DIR, rel)
    return discovered
# 初始化时合并发现的模型
MODEL_FILES.update(discover_models())

# Web data directories for saving uploads and outputs
WEB_DATA_DIR = os.path.join(BASE_DIR, 'web_data')
UPLOAD_DIR = os.path.join(WEB_DATA_DIR, 'uploads')
OUTPUT_DIR = os.path.join(WEB_DATA_DIR, 'outputs')
os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(OUTPUT_DIR, exist_ok=True)

# 提供模型列表给前端动态加载
@app.route('/models', methods=['GET'])
def list_models():
    # 每次请求时也尝试刷新一次，防止运行期间新增权重
    MODEL_FILES.update(discover_models())
    items = []
    for key, path in MODEL_FILES.items():
        display = key
        if key.endswith('best.pt'):
            display = f"{key} (最佳权重)"
        elif key.endswith('yolo11s.pt'):
            display = 'yolo11s.pt (基础模型)'
        elif key.endswith('yolo11n.pt'):
            display = 'yolo11n.pt (基础模型)'
        items.append({'key': key, 'path': path, 'name': display})
    return jsonify({'success': True, 'models': items})


def _get_model(model_key: str):
    """Get or load a YOLO model by key or path (lazy import)."""
    # 如果传入的是存在的路径（相对或绝对），直接使用
    candidate_path = model_key
    if not os.path.isabs(candidate_path):
        candidate_path = os.path.join(BASE_DIR, candidate_path)
    if os.path.exists(candidate_path):
        model_path = candidate_path
    else:
        model_path = MODEL_FILES.get(model_key, None)

    if model_path is None or not os.path.exists(model_path):
        raise FileNotFoundError(f"模型文件不存在: {model_key}")

    # 惰性导入YOLO
    if YOLO is None:
        from ultralytics import YOLO as _YOLO
        model_cls = _YOLO
    else:
        model_cls = YOLO

    if model_path not in _loaded_models:
        _loaded_models[model_path] = model_cls(model_path)
    return _loaded_models[model_path]


def _encode_image_to_base64(img_bgr: np.ndarray) -> str:
    """Encode BGR image to PNG base64 string."""
    success, buffer = cv2.imencode('.png', img_bgr)
    if not success:
        raise RuntimeError('图像编码为PNG失败')
    return base64.b64encode(buffer.tobytes()).decode('utf-8')

# 新增：计算检测框并集覆盖的面积比例，避免重叠重复累计
def _compute_union_area_ratio(xyxy: np.ndarray, img_shape: Tuple[int, int]) -> float:
    h, w = img_shape
    if xyxy is None or xyxy.size == 0:
        return 0.0
    mask = np.zeros((h, w), dtype=np.uint8)
    for x1, y1, x2, y2 in xyxy:
        x1i = max(0, min(int(np.floor(x1)), w - 1))
        y1i = max(0, min(int(np.floor(y1)), h - 1))
        x2i = max(0, min(int(np.ceil(x2)), w))
        y2i = max(0, min(int(np.ceil(y2)), h))
        if x2i <= x1i or y2i <= y1i:
            continue
        mask[y1i:y2i, x1i:x2i] = 255
    covered = int((mask > 0).sum())
    return min(1.0, float(covered) / float(max(1, w * h)))

# 新增：计算分割掩膜的并集覆盖面积比例（仅在结果包含 masks 时使用）
def _compute_union_mask_area_ratio(result, img_shape: Tuple[int, int]) -> float:
    h, w = img_shape
    masks_obj = getattr(result, 'masks', None)
    if masks_obj is None:
        return 0.0

    # 优先使用多边形坐标（通常已缩放到原图尺寸），更精确
    xy_list = getattr(masks_obj, 'xy', None)
    if xy_list:
        mask_union = np.zeros((h, w), dtype=np.uint8)
        try:
            for pts in xy_list:
                if pts is None or len(pts) == 0:
                    continue
                # pts 形状 (N, 2)，单位像素坐标
                poly = np.array(pts, dtype=np.int32)
                # 边界裁剪
                poly[:, 0] = np.clip(poly[:, 0], 0, w - 1)
                poly[:, 1] = np.clip(poly[:, 1], 0, h - 1)
                cv2.fillPoly(mask_union, [poly], 255)
        except Exception:
            # 回退到栅格掩膜
            xy_list = None

        if xy_list:
            covered = int((mask_union > 0).sum())
            return min(1.0, float(covered) / float(max(1, w * h)))

    # 回退：使用栅格掩膜数据并缩放到原图尺寸
    data = getattr(masks_obj, 'data', None)
    if data is None:
        return 0.0
    try:
        masks_np = data.detach().cpu().numpy() if hasattr(data, 'detach') else np.array(data)
        if masks_np.ndim != 3 or masks_np.shape[0] == 0:
            return 0.0
        # 阈值化（有的版本为概率掩膜）
        union_small = (masks_np > 0.5).any(axis=0).astype(np.uint8)  # (mh, mw)
        mh, mw = union_small.shape[:2]
        if mh != h or mw != w:
            # 缩放到原图尺寸
            union = cv2.resize(union_small, (w, h), interpolation=cv2.INTER_NEAREST)
        else:
            union = union_small
        covered = int((union > 0).sum())
        return min(1.0, float(covered) / float(max(1, w * h)))
    except Exception:
        return 0.0
    
def _compute_stats(result, img_shape: Tuple[int, int]) -> Dict:
    """Compute detection statistics from a single Ultralytics result and image shape (h, w)."""
    h, w = img_shape
    boxes = result.boxes
    count = 0
    area_ratio = 0.0
    avg_conf = 0.0

    if boxes is not None and boxes.xyxy is not None:
        xyxy = boxes.xyxy.cpu().numpy()
        count = xyxy.shape[0]
        if count > 0:
            # 若为分割结果，优先使用掩膜并集面积比例；否则使用框并集
            masks_obj = getattr(result, 'masks', None)
            if masks_obj is not None:
                area_ratio = _compute_union_mask_area_ratio(result, (h, w))
            else:
                area_ratio = _compute_union_area_ratio(xyxy, (h, w))
            # 统计平均置信度
            confs = boxes.conf.cpu().numpy() if boxes.conf is not None else np.array([])
            avg_conf = float(confs.mean()) if confs.size > 0 else 0.0

    return {
        'count': int(count),
        'area_ratio': area_ratio,
        'avg_conf': avg_conf,
    }


def _process_image_bytes(file_bytes: bytes, filename: str, model_key: str, conf: float, iou: float, imgsz: int, max_det: int):
    # 解码
    safe_name = os.path.basename(filename or '未命名图像')
    nparr = np.frombuffer(file_bytes, np.uint8)
    img_bgr = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    if img_bgr is None:
        raise RuntimeError('图像解码失败，文件格式可能不支持')
    h, w = img_bgr.shape[:2]

    # 模型
    model = _get_model(model_key)

    # 预测（Ultralytics使用RGB）
    img_rgb = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB)
    results = model.predict(source=img_rgb, conf=conf, iou=iou, imgsz=imgsz, max_det=max_det, verbose=False)
    if not results:
        raise RuntimeError('模型未返回检测结果')
    res = results[0]

    # 可视化
    annotated_rgb = res.plot()
    annotated_bgr = cv2.cvtColor(annotated_rgb, cv2.COLOR_RGB2BGR)
    img_base64 = _encode_image_to_base64(annotated_bgr)

    # 指标
    stats = _compute_stats(res, (h, w))

    # 保存到磁盘
    ts = time.strftime('%Y%m%d-%H%M%S')
    uid = uuid.uuid4().hex[:8]
    name_no_ext, ext = os.path.splitext(safe_name)
    saved_original = os.path.join(UPLOAD_DIR, f'{ts}_{uid}_{safe_name}')
    with open(saved_original, 'wb') as f_out:
        f_out.write(file_bytes)

    def _model_dir_name(model_key: str) -> str:
        key_norm = model_key.replace('\\', '/').strip()
        rel = key_norm
        try:
            if os.path.isabs(model_key):
                rel = os.path.relpath(model_key, BASE_DIR).replace('\\', '/')
        except Exception:
            pass
        parts = rel.split('/')
        if 'runs' in parts and rel.endswith('best.pt'):
            try:
                idx = parts.index('runs')
                run_name = parts[idx + 1] if idx + 1 < len(parts) else None
                if run_name:
                    return run_name
            except ValueError:
                pass
        stem = os.path.splitext(os.path.basename(rel))[0]
        safe = ''.join(ch if ch.isalnum() or ch in ('-', '_', '.') else '_' for ch in stem)
        return safe or 'model_outputs'

    model_subdir = _model_dir_name(model_key)
    per_model_output_dir = os.path.join(OUTPUT_DIR, model_subdir)
    os.makedirs(per_model_output_dir, exist_ok=True)
    saved_output = os.path.join(per_model_output_dir, f'{ts}_{uid}_{name_no_ext}_detected.png')
    cv2.imwrite(saved_output, annotated_bgr)
    rel_original = os.path.relpath(saved_original, BASE_DIR)
    rel_output = os.path.relpath(saved_output, BASE_DIR)

    # 写CSV
    csv_path = os.path.join(WEB_DATA_DIR, 'results.csv')
    write_header = not os.path.exists(csv_path)
    try:
        with open(csv_path, 'a', newline='', encoding='utf-8') as csvfile:
            writer = csv.writer(csvfile)
            if write_header:
                writer.writerow([
                    'timestamp', 'original_filename', 'saved_original_path', 'saved_output_path',
                    'width', 'height', 'count', 'area_ratio', 'avg_conf',
                    'model', 'conf', 'iou', 'imgsz', 'max_det'
                ])
            writer.writerow([
                ts, safe_name, rel_original, rel_output,
                w, h, stats['count'], stats['area_ratio'], stats['avg_conf'],
                model_key, conf, iou, imgsz, max_det
            ])
    except Exception:
        pass

    return {
        'success': True,
        'filename': filename,
        'image_base64': img_base64,
        'metrics': {
            '检测数量': stats['count'],
            '面积比例': stats['area_ratio'],
            '平均置信度': stats['avg_conf'],
        },
        'params': {
            'model': model_key,
            'conf': conf,
            'iou': iou,
            'imgsz': imgsz,
            'max_det': max_det,
        },
        'saved': {
            'original_path': rel_original,
            'output_path': rel_output,
        }
    }


def _queue_worker():
    while True:
        job = _job_queue.get()
        if job is None:
            _job_queue.task_done()
            break
        job_id = job['job_id']
        with _jobs_lock:
            _jobs[job_id] = {'status': 'running'}
        try:
            result = _process_image_bytes(
                job['file_bytes'], job['filename'],
                job['model'], job['conf'], job['iou'], job['imgsz'], job['max_det']
            )
            with _jobs_lock:
                _jobs[job_id] = {'status': 'done', 'result': result}
        except Exception as e:
            with _jobs_lock:
                _jobs[job_id] = {'status': 'error', 'message': str(e)}
        finally:
            _job_queue.task_done()


# 启动后台worker线程
_worker_thread = threading.Thread(target=_queue_worker, daemon=True)
_worker_thread.start()


@app.route('/', methods=['GET'])
def index():
    return render_template('index.html')


def _model_dir_name(model_key: str) -> str:
    """Derive a folder name for outputs based on the selected model.
    - If model is a runs/*/weights/best.pt path, use the run directory name.
    - Else use the basename without extension.
    """
    key_norm = model_key.replace('\\', '/').strip()
    # If absolute path, try to make it relative to BASE_DIR for parsing
    rel = key_norm
    try:
        if os.path.isabs(model_key):
            rel = os.path.relpath(model_key, BASE_DIR).replace('\\', '/')
    except Exception:
        pass
    parts = rel.split('/')
    if 'runs' in parts and rel.endswith('best.pt'):
        # runs/<run_name>/weights/best.pt -> <run_name>
        try:
            idx = parts.index('runs')
            run_name = parts[idx + 1] if idx + 1 < len(parts) else None
            if run_name:
                return run_name
        except ValueError:
            pass
    # fallback to file stem
    stem = os.path.splitext(os.path.basename(rel))[0]
    # sanitize
    safe = ''.join(ch if ch.isalnum() or ch in ('-', '_', '.') else '_' for ch in stem)
    return safe or 'model_outputs'


@app.route('/detect', methods=['POST'])
def detect():
    try:
        # Validate file
        if 'file' not in request.files:
            return jsonify({'success': False, 'message': '未收到文件，请选择要检测的图像'}), 400
        file = request.files['file']
        filename = file.filename or '未命名图像'
        file_bytes = file.read()

        # Params
        model_key = request.form.get('model', 'yolo11s.pt')
        conf = float(request.form.get('conf', 0.25))
        iou = float(request.form.get('iou', 0.45))
        imgsz = int(request.form.get('imgsz', 640))
        max_det = int(request.form.get('max_det', 300))

        result = _process_image_bytes(file_bytes, filename, model_key, conf, iou, imgsz, max_det)
        return jsonify(result)
    except FileNotFoundError as e:
        return jsonify({'success': False, 'message': str(e)}), 400
    except Exception as e:
        return jsonify({'success': False, 'message': f'检测失败: {str(e)}'}), 500


@app.route('/enqueue', methods=['POST'])
def enqueue():
    try:
        if 'file' not in request.files:
            return jsonify({'success': False, 'message': '未收到文件，请选择要检测的图像'}), 400
        file = request.files['file']
        filename = file.filename or '未命名图像'
        file_bytes = file.read()

        model_key = request.form.get('model', 'yolo11s.pt')
        conf = float(request.form.get('conf', 0.25))
        iou = float(request.form.get('iou', 0.45))
        imgsz = int(request.form.get('imgsz', 640))
        max_det = int(request.form.get('max_det', 300))

        job_id = uuid.uuid4().hex
        with _jobs_lock:
            _jobs[job_id] = {'status': 'queued'}
        _job_queue.put({
            'job_id': job_id,
            'file_bytes': file_bytes,
            'filename': filename,
            'model': model_key,
            'conf': conf,
            'iou': iou,
            'imgsz': imgsz,
            'max_det': max_det,
        })
        return jsonify({'success': True, 'job_id': job_id})
    except Exception as e:
        return jsonify({'success': False, 'message': f'入队失败: {str(e)}'}), 500


@app.route('/jobs/<job_id>', methods=['GET'])
def job_status(job_id: str):
    with _jobs_lock:
        info = _jobs.get(job_id)
    if not info:
        return jsonify({'success': False, 'status': 'not_found'}), 404
    if info.get('status') == 'done':
        return jsonify({'success': True, 'status': 'done', 'result': info.get('result')})
    elif info.get('status') == 'error':
        return jsonify({'success': False, 'status': 'error', 'message': info.get('message', '未知错误')}), 500
    else:
        return jsonify({'success': True, 'status': info.get('status', 'queued')})


if __name__ == '__main__':
    # Run development server
    app.run(host='127.0.0.1', port=8000, debug=False)
