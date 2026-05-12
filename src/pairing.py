"""输入验证和 Case_Pair 配对逻辑"""

import json
import os
from pathlib import Path

from src.config import MAX_BATCH_SIZE
from src.models import CasePair

IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp"}


def find_case_pairs(input_dir: str) -> tuple[list[CasePair], list[str]]:
    """
    扫描 input_dir，按文件名 stem 配对图片和 JSON。

    Returns:
        (pairs, errors): 配对成功的列表 + 错误信息列表
    """
    input_path = Path(input_dir)
    if not input_path.exists():
        return [], [f"输入目录不存在: {input_dir}"]

    # 收集所有文件，按 stem 分组
    images: dict[str, str] = {}
    jsons: dict[str, str] = {}

    for f in input_path.iterdir():
        if not f.is_file():
            continue
        stem = f.stem
        suffix = f.suffix.lower()
        if suffix in IMAGE_EXTENSIONS:
            images[stem] = str(f)
        elif suffix == ".json":
            jsons[stem] = str(f)

    # 配对
    pairs: list[CasePair] = []
    errors: list[str] = []

    all_stems = set(images.keys()) | set(jsons.keys())
    for stem in sorted(all_stems):
        has_image = stem in images
        has_json = stem in jsons

        if has_image and has_json:
            # 尝试加载 JSON
            try:
                with open(jsons[stem], "r", encoding="utf-8") as jf:
                    product_data = json.load(jf)
            except (json.JSONDecodeError, IOError) as e:
                errors.append(f"JSON 解析失败 [{stem}]: {e}")
                continue

            pairs.append(CasePair(
                case_id=stem,
                image_path=images[stem],
                json_path=jsons[stem],
                product_data=product_data,
            ))
        elif has_image and not has_json:
            errors.append(f"缺少 JSON 文件: {stem} (有图片 {images[stem]})")
        elif has_json and not has_image:
            errors.append(f"缺少图片文件: {stem} (有 JSON {jsons[stem]})")

    return pairs, errors


def validate_batch(pairs: list[CasePair], errors: list[str]) -> tuple[list[CasePair], list[str]]:
    """
    验证批量大小限制。

    Returns:
        (pairs, errors): 如果超限则 pairs 为空，errors 包含超限信息
    """
    if len(pairs) > MAX_BATCH_SIZE:
        return [], [f"批量超限: 提交了 {len(pairs)} 个案例，上限为 {MAX_BATCH_SIZE}"]
    return pairs, errors
