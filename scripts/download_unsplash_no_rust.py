import os
import time
import json
import argparse
from typing import Dict, Any, Set

import requests


"""
Unsplash 批量下载脚本（合规版）

功能：
- 使用 Unsplash 官方 API 按关键词分页检索，并通过 links.download_location 注册下载以获取真实下载 URL；
- 保存图片到 datasets_noRust/images；为 YOLO 负样本创建同名空标签到 datasets_noRust/labels；
- 保存元信息（作者、来源、署名）到 datasets_noRust/images/<id>.json，便于溯源与合规。

使用方法：
1) 环境变量设置：UNSPLASH_ACCESS_KEY=你的AccessKey（在 https://unsplash.com/developers 创建应用）
2) 运行示例：
   python scripts/download_unsplash_no_rust.py \
     --query "metal facade, aluminum cladding, clean metal facade" \
     --pages 5 --per_page 30 \
     --out_root datasets_noRust

注意：
- 必须通过 download_location 注册下载，直接抓页面原图会违反服务条款；
- 遵守速率限制与配额（免费应用较低），本脚本已做轻量限速；
- 仅用于收集“无锈蚀/基本无锈蚀”负样本，请配合人工抽检质量。
"""


DEFAULT_QUERY = "metal facade, aluminum cladding, clean metal facade"


def make_session(access_key: str) -> requests.Session:
    s = requests.Session()
    s.headers.update({
        "Accept-Version": "v1",
        "Authorization": f"Client-ID {access_key}",
        "User-Agent": "RustDetectionDownloader/1.0",
    })
    return s


def search_page(session: requests.Session, query: str, page: int, per_page: int) -> Any:
    url = "https://api.unsplash.com/search/photos"
    params = {
        "query": query,
        "page": page,
        "per_page": per_page,
        "orientation": "landscape",
        "content_filter": "high",
        "order_by": "relevant",
    }
    r = session.get(url, params=params, timeout=30)
    r.raise_for_status()
    return r.json().get("results", [])


def register_and_get_download_url(session: requests.Session, download_location: str) -> str:
    r = session.get(download_location, timeout=30)
    r.raise_for_status()
    data = r.json()
    return data["url"]


def save_photo(session: requests.Session, photo: Dict[str, Any], images_dir: str, labels_dir: str, query: str) -> None:
    pid = photo["id"]
    dl_loc = photo["links"]["download_location"]
    real_url = register_and_get_download_url(session, dl_loc)

    # 目标文件
    img_path = os.path.join(images_dir, f"{pid}.jpg")
    meta_path = os.path.join(images_dir, f"{pid}.json")
    label_path = os.path.join(labels_dir, f"{pid}.txt")

    # 下载图片（若已存在则跳过下载，但仍确保标签与元信息存在）
    downloaded_new = False
    if not os.path.exists(img_path):
        ir = session.get(real_url, stream=True, timeout=60)
        ir.raise_for_status()
        with open(img_path, "wb") as f:
            for chunk in ir.iter_content(chunk_size=1 << 16):
                if chunk:
                    f.write(chunk)
        time.sleep(0.5)  # 轻量限速
        downloaded_new = True

    # 写入空标签（负样本，无目标）
    if not os.path.exists(label_path):
        with open(label_path, "w", encoding="utf-8") as f:
            f.write("")

    # 保存元信息与署名
    user = photo.get("user", {})
    meta = {
        "id": pid,
        "author": user.get("name"),
        "username": user.get("username"),
        "profile": (user.get("links", {}) or {}).get("html"),
        "unsplash_page": photo.get("links", {}).get("html"),
        "alt": photo.get("alt_description") or "",
        "query": query,
        "source": "Unsplash",
        "attribution": f"Photo by {user.get('name')} on Unsplash" if user.get("name") else "Unsplash",
    }
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)

    return downloaded_new


def main():
    parser = argparse.ArgumentParser(description="Unsplash 批量下载（无锈蚀负样本）")
    parser.add_argument("--query", type=str, default=DEFAULT_QUERY, help="检索关键词（可中英文混合）")
    parser.add_argument("--pages", type=int, default=5, help="分页页数")
    parser.add_argument("--per_page", type=int, default=30, help="每页数量（最大30）")
    parser.add_argument("--out_root", type=str, default=os.path.join("datasets_noRust"), help="输出根目录")
    parser.add_argument("--count", type=int, default=None, help="新下载的目标数量（去重后）")
    args = parser.parse_args()

    access_key = os.environ.get("UNSPLASH_ACCESS_KEY", "").strip()
    if not access_key:
        raise RuntimeError("未设置 UNSPLASH_ACCESS_KEY 环境变量，请先在 Unsplash 开发者平台创建应用并设置 Access Key")

    images_dir = os.path.join(args.out_root, "images")
    labels_dir = os.path.join(args.out_root, "labels")
    os.makedirs(images_dir, exist_ok=True)
    os.makedirs(labels_dir, exist_ok=True)

    session = make_session(access_key)

    # 已有图片 ID 集合（用于去重）
    def load_existing_ids(images_path: str) -> Set[str]:
        ids: Set[str] = set()
        try:
            for fn in os.listdir(images_path):
                if fn.lower().endswith(".jpg"):
                    ids.add(os.path.splitext(fn)[0])
        except FileNotFoundError:
            pass
        return ids

    existing_ids = load_existing_ids(images_dir)

    total_saved = 0
    for page in range(1, args.pages + 1):
        try:
            results = search_page(session, args.query, page, args.per_page)
        except Exception as e:
            print(f"[WARN] 搜索失败（page={page}）：{e}")
            time.sleep(5)
            continue
        if not results:
            print(f"[INFO] 第 {page} 页无结果，提前结束")
            break
        print(f"[INFO] 第 {page} 页：{len(results)} 张")
        for photo in results:
            pid = photo.get("id")
            if pid in existing_ids:
                print(f"[SKIP] 已存在 id={pid}")
                continue
            try:
                new_saved = save_photo(session, photo, images_dir, labels_dir, args.query)
                if new_saved:
                    total_saved += 1
                    existing_ids.add(pid)
                else:
                    print(f"[SKIP] 文件已存在 id={pid}")
            except Exception as e:
                print(f"[WARN] 保存失败 id={photo.get('id')}: {e}")
                time.sleep(2)

            # 达到目标数量则提前结束
            if args.count is not None and total_saved >= args.count:
                print(f"[INFO] 已达目标数量 {args.count}，停止下载")
                break
        time.sleep(1)  # 页间限速

        if args.count is not None and total_saved >= args.count:
            break

    print(f"[DONE] 本次新增保存 {total_saved} 张至 {images_dir}（已去重），并在 {labels_dir} 生成空标签")


if __name__ == "__main__":
    main()
