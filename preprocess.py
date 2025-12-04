import os
import sys
import argparse
from pathlib import Path
import shutil
import cv2
import numpy as np
import yaml


IMG_EXTS = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}


def ensure_dir(p: Path):
    p.mkdir(parents=True, exist_ok=True)


def gray_world_white_balance(img: np.ndarray) -> np.ndarray:
    img = img.astype(np.float32)
    avg_b, avg_g, avg_r = np.mean(img[:, :, 0]), np.mean(img[:, :, 1]), np.mean(img[:, :, 2])
    avg_gray = (avg_b + avg_g + avg_r) / 3.0
    img[:, :, 0] *= (avg_gray / (avg_b + 1e-6))
    img[:, :, 1] *= (avg_gray / (avg_g + 1e-6))
    img[:, :, 2] *= (avg_gray / (avg_r + 1e-6))
    img = np.clip(img, 0, 255).astype(np.uint8)
    return img


def clahe_lab(img: np.ndarray, clip_limit: float = 2.0, tile_grid_size: int = 8) -> np.ndarray:
    lab = cv2.cvtColor(img, cv2.COLOR_BGR2Lab)
    l, a, b = cv2.split(lab)
    clahe = cv2.createCLAHE(clipLimit=clip_limit, tileGridSize=(tile_grid_size, tile_grid_size))
    l2 = clahe.apply(l)
    lab2 = cv2.merge([l2, a, b])
    return cv2.cvtColor(lab2, cv2.COLOR_Lab2BGR)


def msr_retinex(img: np.ndarray, scales=(15, 80, 250), weights=None) -> np.ndarray:
    # Simple Multiscale Retinex implementation
    if weights is None:
        weights = [1.0 / len(scales)] * len(scales)
    img = img.astype(np.float32) + 1.0
    retinex = np.zeros_like(img)
    for s, w in zip(scales, weights):
        blur = cv2.GaussianBlur(img, (0, 0), sigmaX=s, sigmaY=s)
        retinex += w * (np.log(img) - np.log(blur + 1.0))
    # Normalize
    retinex = (retinex - np.min(retinex)) / (np.max(retinex) - np.min(retinex) + 1e-6)
    retinex = (retinex * 255.0).astype(np.uint8)
    return retinex


def highlight_mask_hsv(img: np.ndarray, v_thresh: int = 220, s_thresh: int = 60) -> np.ndarray:
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    h, s, v = cv2.split(hsv)
    mask = (v >= v_thresh) & (s <= s_thresh)
    mask = mask.astype(np.uint8) * 255
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel, iterations=2)
    return mask


def reduce_highlights(img: np.ndarray, mask: np.ndarray, dim_ratio: float = 0.7) -> np.ndarray:
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    h, s, v = cv2.split(hsv)
    v = v.astype(np.float32)
    v[mask > 0] *= dim_ratio
    v = np.clip(v, 0, 255).astype(np.uint8)
    hsv2 = cv2.merge([h, s, v])
    return cv2.cvtColor(hsv2, cv2.COLOR_HSV2BGR)


def inpaint_highlights(img: np.ndarray, mask: np.ndarray, radius: int = 3) -> np.ndarray:
    return cv2.inpaint(img, mask, radius, cv2.INPAINT_TELEA)


def denoise(img: np.ndarray, bilateral_cfg: dict | None, nlm_cfg: dict | None) -> np.ndarray:
    out = img.copy()
    if bilateral_cfg and bilateral_cfg.get("enabled", False):
        d = int(bilateral_cfg.get("d", 9))
        sigmaColor = float(bilateral_cfg.get("sigmaColor", 75))
        sigmaSpace = float(bilateral_cfg.get("sigmaSpace", 75))
        out = cv2.bilateralFilter(out, d, sigmaColor, sigmaSpace)
    if nlm_cfg and nlm_cfg.get("enabled", False):
        h = float(nlm_cfg.get("h", 7))
        hColor = float(nlm_cfg.get("hColor", 7))
        templateWindowSize = int(nlm_cfg.get("templateWindowSize", 7))
        searchWindowSize = int(nlm_cfg.get("searchWindowSize", 21))
        out = cv2.fastNlMeansDenoisingColored(out, None, h, hColor, templateWindowSize, searchWindowSize)
    return out


def simple_background_mask(img: np.ndarray, method: str = "none", cfg: dict | None = None) -> np.ndarray:
    if method == "none":
        return np.ones(img.shape[:2], dtype=np.uint8) * 255
    # Example: use saturation threshold to keep high-saturation areas (heuristic)
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    s = hsv[:, :, 1]
    if method == "sat_otsu":
        _, m = cv2.threshold(s, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    else:
        thr = int((cfg or {}).get("sat_thresh", 50))
        _, m = cv2.threshold(s, thr, 255, cv2.THRESH_BINARY)
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
    m = cv2.morphologyEx(m, cv2.MORPH_OPEN, kernel, iterations=1)
    m = cv2.morphologyEx(m, cv2.MORPH_CLOSE, kernel, iterations=1)
    return m


def apply_background_mask(img: np.ndarray, mask: np.ndarray, strength: float = 0.6) -> np.ndarray:
    # Attenuate background brightness to reduce interference
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    h, s, v = cv2.split(hsv)
    v = v.astype(np.float32)
    v[mask == 0] *= strength
    v = np.clip(v, 0, 255).astype(np.uint8)
    hsv2 = cv2.merge([h, s, v])
    return cv2.cvtColor(hsv2, cv2.COLOR_HSV2BGR)


def preprocess_image(img: np.ndarray, cfg: dict) -> tuple[np.ndarray, dict]:
    info = {}
    out = img.copy()

    # 1) White balance
    if cfg.get("white_balance", {}).get("enabled", True):
        out = gray_world_white_balance(out)
        info["white_balance"] = True

    # 2) Illumination normalization
    il_cfg = cfg.get("illumination", {})
    if il_cfg.get("clahe", {}).get("enabled", True):
        out = clahe_lab(out, il_cfg.get("clahe", {}).get("clipLimit", 2.0), il_cfg.get("clahe", {}).get("tileGridSize", 8))
        info["clahe"] = True
    if il_cfg.get("retinex", {}).get("enabled", False):
        scales = il_cfg.get("retinex", {}).get("scales", [15, 80, 250])
        out = msr_retinex(out, scales=scales)
        info["retinex"] = True

    # 3) De-reflection
    dr_cfg = cfg.get("de_reflection", {})
    if dr_cfg.get("enabled", True):
        mask = highlight_mask_hsv(out, v_thresh=dr_cfg.get("v_thresh", 220), s_thresh=dr_cfg.get("s_thresh", 60))
        mode = dr_cfg.get("mode", "dim")
        if mode == "dim":
            out = reduce_highlights(out, mask, dim_ratio=float(dr_cfg.get("dim_ratio", 0.7)))
            info["de_reflection"] = "dim"
        elif mode == "inpaint":
            out = inpaint_highlights(out, mask, radius=int(dr_cfg.get("inpaint_radius", 3)))
            info["de_reflection"] = "inpaint"

    # 4) Denoise
    out = denoise(out, cfg.get("bilateral", {"enabled": True}), cfg.get("nlm", {"enabled": False}))
    info["denoise"] = True

    # 5) Background attenuation
    bg_cfg = cfg.get("background", {"method": "none"})
    mask = simple_background_mask(out, method=bg_cfg.get("method", "none"), cfg=bg_cfg)
    if bg_cfg.get("method", "none") != "none":
        out = apply_background_mask(out, mask, strength=float(bg_cfg.get("strength", 0.6)))
        info["background_mask"] = bg_cfg.get("method")

    return out, info


def load_config(cfg_path: Path | None) -> dict:
    default_cfg = {
        "white_balance": {"enabled": True},
        "illumination": {
            "clahe": {"enabled": True, "clipLimit": 2.0, "tileGridSize": 8},
            "retinex": {"enabled": False, "scales": [15, 80, 250]},
        },
        "de_reflection": {"enabled": True, "v_thresh": 220, "s_thresh": 60, "mode": "dim", "dim_ratio": 0.7, "inpaint_radius": 3},
        "bilateral": {"enabled": True, "d": 9, "sigmaColor": 75, "sigmaSpace": 75},
        "nlm": {"enabled": False, "h": 7, "hColor": 7, "templateWindowSize": 7, "searchWindowSize": 21},
        "background": {"method": "none", "sat_thresh": 50, "strength": 0.6},
    }
    if cfg_path and cfg_path.exists():
        with open(cfg_path, "r", encoding="utf-8") as f:
            user_cfg = yaml.safe_load(f) or {}
        # shallow merge
        for k, v in user_cfg.items():
            if isinstance(v, dict) and isinstance(default_cfg.get(k), dict):
                default_cfg[k].update(v)
            else:
                default_cfg[k] = v
    return default_cfg


def is_image_file(p: Path) -> bool:
    return p.suffix.lower() in IMG_EXTS


def process_split(src_root: Path, dst_root: Path, split: str, cfg: dict, preview: bool):
    src_img_dir = src_root / split / "images"
    src_lbl_dir = src_root / split / "labels"
    dst_img_dir = dst_root / split / "images"
    dst_lbl_dir = dst_root / split / "labels"
    preview_dir = dst_root / "preview" / split
    ensure_dir(dst_img_dir)
    ensure_dir(dst_lbl_dir)
    if preview:
        ensure_dir(preview_dir)

    # copy labels directly
    if src_lbl_dir.exists():
        for lbl in src_lbl_dir.rglob("*.txt"):
            rel = lbl.relative_to(src_lbl_dir)
            ensure_dir((dst_lbl_dir / rel).parent)
            shutil.copy2(lbl, dst_lbl_dir / rel)

    count = 0
    for img_p in src_img_dir.rglob("*"):
        if not img_p.is_file() or not is_image_file(img_p):
            continue
        rel = img_p.relative_to(src_img_dir)
        out_path = dst_img_dir / rel
        ensure_dir(out_path.parent)

        img = cv2.imread(str(img_p))
        if img is None:
            print(f"[WARN] Failed to read image: {img_p}")
            continue
        proc, _ = preprocess_image(img, cfg)
        cv2.imwrite(str(out_path), proc)
        count += 1

        if preview:
            # side-by-side comparison
            h = max(img.shape[0], proc.shape[0])
            w = img.shape[1] + proc.shape[1]
            canvas = np.zeros((h, w, 3), dtype=np.uint8)
            canvas[: img.shape[0], : img.shape[1]] = img
            canvas[: proc.shape[0], img.shape[1] : img.shape[1] + proc.shape[1]] = proc
            prev_path = preview_dir / rel
            ensure_dir(prev_path.parent)
            cv2.imwrite(str(prev_path), canvas)

    print(f"[Split {split}] processed images: {count}")


def main():
    parser = argparse.ArgumentParser(description="Preprocess dataset images with configurable pipeline")
    parser.add_argument("--src", type=str, default="datasets", help="Source datasets directory")
    parser.add_argument("--dst", type=str, default="datasets_preprocessed", help="Destination datasets directory")
    parser.add_argument("--config", type=str, default="preprocess_config.yaml", help="YAML config path")
    parser.add_argument("--preview", action="store_true", help="Generate side-by-side preview")
    args = parser.parse_args()

    src_root = Path(args.src).resolve()
    dst_root = Path(args.dst).resolve()
    cfg_path = Path(args.config).resolve()

    if not src_root.exists():
        print(f"[ERROR] Source directory not found: {src_root}")
        sys.exit(1)

    ensure_dir(dst_root)
    cfg = load_config(cfg_path)

    for split in ["train", "valid", "test"]:
        process_split(src_root, dst_root, split, cfg, preview=args.preview)

    print(f"[DONE] Output dataset: {dst_root}")


if __name__ == "__main__":
    main()