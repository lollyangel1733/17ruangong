"""
YOLO11 训练脚本（Python 接口）
用法（终端):
  python train.py --epochs 100 --imgsz 640
可选参数:
  --weights 默认 yolo11n.pt（也可指定上次 best.pt 以继续微调）
  --data    默认 datasets/data.yaml
  --epochs  训练轮次，默认 100
  --imgsz   图像尺寸，默认 640
  --batch   批大小（不填则自动按显存选择: CUDA=16, CPU=8）
  --optimizer 优化器，默认 SGD，可选 SGD/Adam/AdamW
  --lr0     初始学习率（不填则按优化器自动: SGD=0.01, Adam/AdamW=0.001）
  --device  设备（不填则自动: CUDA 用 "0"，否则 "cpu"）
  --skip_test 训练结束后不评估 test（默认会评估）
  --eval_only 仅进行测试集评估并输出报告（不训练）
  --report_out 评估报告保存路径（txt），默认保存到评估目录 metrics_report.txt
  --patience 早停耐心值（验证指标无提升的连续轮次阈值），默认 20
  --freeze   冻结前 N 层进行微调（可选），默认不冻结
  --resume   从当前权重的训练状态继续（仅当提供 last.pt 时更适用）
"""
import argparse
import sys
import os
import re

try:
    import torch
    import cv2
    from ultralytics import YOLO
except Exception as e:
    print(f"[ERROR] 依赖导入失败: {e}")
    print("请确保已安装: pip install ultralytics torch opencv-python")
    sys.exit(1)


def format_eval_report(eval_results, eval_model, results=None):
    """
    将评估指标整理为文本报告字符串。
    """
    lines = []
    lines.append("[Eval] test 集评估完成。")
    try:
        box = getattr(eval_results, "box", None)
        names = getattr(eval_model, "names", None)
        if box is not None:
            map50 = getattr(box, "map50", None)
            map5095 = getattr(box, "map", None)
            mp = getattr(box, "mp", None)   # mean precision
            mr = getattr(box, "mr", None)   # mean recall
            mf1 = getattr(box, "mf1", None) # mean F1（若可用）
            lines.append("[Eval] Overall:")
            if map50 is not None:
                lines.append(f"  mAP@0.50: {map50:.4f}")
            if map5095 is not None:
                lines.append(f"  mAP@0.50:0.95: {map5095:.4f}")
            if mp is not None:
                lines.append(f"  Mean Precision: {mp:.4f}")
            if mr is not None:
                lines.append(f"  Mean Recall: {mr:.4f}")
            if mf1 is not None:
                lines.append(f"  Mean F1: {mf1:.4f}")

            maps = getattr(box, "maps", None)  # per-class mAP@0.50:0.95
            p_list = getattr(box, "p", None)   # per-class precision（若可用）
            r_list = getattr(box, "r", None)   # per-class recall（若可用）
            if maps is not None and isinstance(maps, (list, tuple)):
                lines.append("[Eval] Per-class metrics:")
                for i, ap in enumerate(maps):
                    cls_name = names.get(i, str(i)) if isinstance(names, dict) else str(i)
                    msg = f"  class {i} ({cls_name}): mAP@0.50:0.95={ap:.4f}"
                    if isinstance(p_list, (list, tuple)) and i < len(p_list) and p_list[i] is not None:
                        msg += f", Precision={p_list[i]:.4f}"
                    if isinstance(r_list, (list, tuple)) and i < len(r_list) and r_list[i] is not None:
                        msg += f", Recall={r_list[i]:.4f}"
                    lines.append(msg)
            else:
                lines.append("[Eval] 未提供每类 mAP 列表（maps），可能与当前 Ultralytics 版本有关。")

        # 输出目录提示
        save_dir = getattr(eval_results, "save_dir", getattr(results, "save_dir", None))
        if save_dir:
            lines.append("[Eval] 可视化输出目录:")
            lines.append(f"  {save_dir}")
            lines.append("  - 包含 PR/F1/P/R 曲线图、混淆矩阵、预测示例等（不同版本可能略有差异）")
        else:
            lines.append("[Eval] 未获取到评估输出目录 save_dir。")
    except Exception as e:
        lines.append(f"[WARN] 详细指标整理失败：{e}")
    return "\n".join(lines)


def save_report(text, report_path):
    try:
        os.makedirs(os.path.dirname(report_path), exist_ok=True)
        with open(report_path, "w", encoding="utf-8") as f:
            f.write(text)
        print(f"[Eval] 已保存评估报告: {report_path}")
    except Exception as e:
        print(f"[WARN] 评估报告保存失败: {e}")


def main():
    parser = argparse.ArgumentParser(description="YOLO11 训练入口")
    parser.add_argument("--weights", type=str, default="yolo11n.pt", help="预训练权重路径")
    parser.add_argument("--data", type=str, default="datasets/data.yaml", help="数据集配置文件路径 (默认 datasets/data.yaml)")
    parser.add_argument("--epochs", type=int, default=100, help="训练轮次")
    parser.add_argument("--imgsz", type=int, default=640, help="训练图像尺寸")
    parser.add_argument("--batch", type=int, default=None, help="批大小（不填自动选择）")
    parser.add_argument("--optimizer", type=str, default="SGD", choices=["SGD", "Adam", "AdamW"], help="优化器类型")
    parser.add_argument("--lr0", type=float, default=None, help="初始学习率（不填自动）")
    parser.add_argument("--device", type=str, default=None, help="训练设备，例如 '0' 或 'cpu'")
    parser.add_argument("--skip_test", action="store_true", help="训练结束后不评估 test")
    parser.add_argument("--eval_only", action="store_true", help="仅进行测试集评估并输出报告（不训练）")
    parser.add_argument("--report_out", type=str, default=None, help="评估报告保存路径（txt），默认保存到评估目录 metrics_report.txt")
    parser.add_argument("--patience", type=int, default=20, help="早停耐心值（验证指标无提升的连续轮次阈值）")
    parser.add_argument("--freeze", type=int, default=None, help="冻结前 N 层进行微调（可选）")
    parser.add_argument("--resume", action="store_true", help="从当前权重的训练状态继续（仅当提供 last.pt 时更适用）")
    parser.add_argument("--name_suffix", type=str, default="", help="为输出 run 名称追加后缀，便于对比（例如 _preproc）")
    args = parser.parse_args()

    cuda_available = torch.cuda.is_available()
    cuda_ver = torch.version.cuda if hasattr(torch.version, "cuda") else "unknown"
    print(f"[Env] Torch: {torch.__version__}, CUDA available: {cuda_available}, CUDA version: {cuda_ver}")
    print(f"[Env] OpenCV: {cv2.__version__}")

    # 自动设备选择
    if args.device is None:
        args.device = "0" if cuda_available else "cpu"

    # 自动批大小选择
    if args.batch is None:
        args.batch = 16 if cuda_available else 8

    # 自动学习率选择
    if args.lr0 is None:
        if args.optimizer.upper() == "SGD":
            args.lr0 = 0.01
        else:
            args.lr0 = 0.001

    print("[Config] weights=", args.weights)
    print("[Config] data=", args.data)
    print("[Config] epochs=", args.epochs, ", imgsz=", args.imgsz)
    print("[Config] batch=", args.batch, ", optimizer=", args.optimizer, ", lr0=", args.lr0)
    print("[Config] device=", args.device)
    print("[Config] patience=", args.patience, ", freeze=", args.freeze, ", resume=", args.resume)

    # 自动推断 run 名称（基于权重文件名，如 yolo11s.pt -> rust_yolo11s_train）
    _weights_bn = os.path.basename(args.weights)
    _model_tag = None
    try:
        _m = re.match(r'^(yolo[\w\d]+)\.pt$', _weights_bn, re.IGNORECASE)
        _model_tag = _m.group(1) if _m else None
    except Exception:
        _model_tag = None
    train_name = (f"rust_{_model_tag}_train" if _model_tag else "rust_custom_train") + (args.name_suffix or "")
    test_name = (f"rust_{_model_tag}_train_test" if _model_tag else "rust_custom_train_test") + (args.name_suffix or "")
    # 仅评估模式
    if args.eval_only:
        print("[EvalOnly] 进入仅评估模式（不训练）...")
        try:
            if not os.path.exists(args.weights):
                print(f"[ERROR] 指定权重不存在: {args.weights}")
                sys.exit(1)
            eval_model = YOLO(args.weights)
            eval_results = eval_model.val(
                data=args.data,
                split="test",
                imgsz=args.imgsz,
                batch=args.batch,
                device=args.device,
                workers=0,
                project="runs",
                name=test_name
            )
            print(eval_results)
            # 整理与保存报告
            report_text = format_eval_report(eval_results, eval_model)
            save_dir = getattr(eval_results, "save_dir", None)
            report_path = args.report_out or (os.path.join(save_dir, "metrics_report.txt") if save_dir else os.path.join("runs", test_name, "metrics_report.txt"))
            save_report(report_text, report_path)
            return
        except Exception as e:
            print(f"[ERROR] 仅评估模式出错: {e}")
            sys.exit(1)

    try:
        model = YOLO(args.weights)
        results = model.train(
            data=args.data,
            epochs=args.epochs,
            imgsz=args.imgsz,
            batch=args.batch,
            device=args.device,
            optimizer=args.optimizer,
            lr0=args.lr0,
            patience=args.patience,
            freeze=args.freeze,
            resume=args.resume,
            workers=0,              # Windows 上多进程可能不稳定，设为 0 更稳妥
            project="runs",
            name=train_name
        )
        print("[Train] 训练完成。结果目录可在 runs/ 下查看。")
        print(results)

        # 自动在 test 集评估（除非显式跳过）
        if not args.skip_test:
            print("[Eval] 开始在 test 集评估最佳权重...")
            try:
                save_dir = getattr(results, "save_dir", None)
                best_path = os.path.join(save_dir, "weights", "best.pt") if save_dir else None
                if best_path and os.path.exists(best_path):
                    eval_model = YOLO(best_path)
                else:
                    print("[Eval] 未找到 best.pt，改用当前模型进行评估。")
                    eval_model = model
                eval_results = eval_model.val(
                    data=args.data,
                    split="test",
                    imgsz=args.imgsz,
                    batch=args.batch,
                    device=args.device,
                    workers=0,
                    project="runs",
                    name=test_name
                )
                print("[Eval] test 集评估完成。")
                print(eval_results)

                # 详细指标打印（尽可能多且安全）
                try:
                    box = getattr(eval_results, "box", None)
                    names = getattr(eval_model, "names", None)
                    if box is not None:
                        map50 = getattr(box, "map50", None)
                        map5095 = getattr(box, "map", None)
                        mp = getattr(box, "mp", None)   # mean precision
                        mr = getattr(box, "mr", None)   # mean recall
                        mf1 = getattr(box, "mf1", None) # mean F1（若可用）
                        print("[Eval] Overall:")
                        if map50 is not None:
                            print(f"  mAP@0.50: {map50:.4f}")
                        if map5095 is not None:
                            print(f"  mAP@0.50:0.95: {map5095:.4f}")
                        if mp is not None:
                            print(f"  Mean Precision: {mp:.4f}")
                        if mr is not None:
                            print(f"  Mean Recall: {mr:.4f}")
                        if mf1 is not None:
                            print(f"  Mean F1: {mf1:.4f}")

                        maps = getattr(box, "maps", None)  # per-class mAP@0.50:0.95
                        p_list = getattr(box, "p", None)   # per-class precision（若可用）
                        r_list = getattr(box, "r", None)   # per-class recall（若可用）
                        if maps is not None and isinstance(maps, (list, tuple)):
                            print("[Eval] Per-class metrics:")
                            for i, ap in enumerate(maps):
                                cls_name = names.get(i, str(i)) if isinstance(names, dict) else str(i)
                                msg = f"  class {i} ({cls_name}): mAP@0.50:0.95={ap:.4f}"
                                # 附加 per-class P/R（如果存在）
                                if isinstance(p_list, (list, tuple)) and i < len(p_list) and p_list[i] is not None:
                                    msg += f", Precision={p_list[i]:.4f}"
                                if isinstance(r_list, (list, tuple)) and i < len(r_list) and r_list[i] is not None:
                                    msg += f", Recall={r_list[i]:.4f}"
                                print(msg)
                        else:
                            print("[Eval] 未提供每类 mAP 列表（maps），可能与当前 Ultralytics 版本有关。")

                    # 速度与曲线文件位置（如可用）
                    save_dir = getattr(eval_results, "save_dir", getattr(results, "save_dir", None))
                    if save_dir:
                        print("[Eval] 可视化输出目录:")
                        print(f"  {save_dir}")
                        print("  - 包含 PR/F1/P/R 曲线图、混淆矩阵、预测示例等（不同版本可能略有差异）")
                        # 同步保存报告
                        report_text = format_eval_report(eval_results, eval_model, results)
                        report_path = os.path.join(save_dir, "metrics_report.txt")
                        save_report(report_text, report_path)
                    else:
                        print("[Eval] 未获取到评估输出目录 save_dir。")
                except Exception as e:
                    print(f"[WARN] 详细指标打印失败：{e}")
            except Exception as e:
                print(f"[ERROR] test 集评估出错: {e}")

    except Exception as e:
        print(f"[ERROR] 训练过程出错: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()