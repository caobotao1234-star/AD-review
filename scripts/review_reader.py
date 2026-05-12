"""
人工复核结果回读脚本

用法：
    python scripts/review_reader.py

功能：
    读取 review_queue/ 目录中已填写 human_decision 的 JSON 文件，
    汇总复核结果并打印。

复核流程：
    1. 运行 main.py 后，低置信度案例会写入 review_queue/ 目录
    2. 复核员打开对应 JSON 文件，填写 human_decision 字段（如 "通过"/"下架"/"限流"）
    3. 可选填写 review_notes 字段添加备注
    4. 运行本脚本查看复核结果汇总
"""

import sys
from pathlib import Path

project_root = str(Path(__file__).parent.parent)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from src.review_queue import read_review_decisions


def main():
    print("=" * 60)
    print("📋 人工复核结果汇总")
    print("=" * 60)

    decisions = read_review_decisions()

    if not decisions:
        print("\n暂无已复核的案例。")
        print("提示：请在 review_queue/ 目录中的 JSON 文件里填写 human_decision 字段。")
        return

    print(f"\n已复核案例: {len(decisions)} 个\n")

    for d in decisions:
        print(f"  案例: {d['case_id']}")
        print(f"  用户: {d['user_id']}")
        print(f"  Agent建议: {d['recommended_action']}")
        print(f"  人工决定: {d['human_decision']}")
        if d.get("review_notes"):
            print(f"  备注: {d['review_notes']}")
        agree = "✅ 一致" if d['human_decision'] == d['recommended_action'] else "⚠️ 不一致"
        print(f"  人机对比: {agree}")
        print()

    # 统计
    agree_count = sum(1 for d in decisions if d['human_decision'] == d['recommended_action'])
    print(f"{'─' * 40}")
    print(f"人机一致率: {agree_count}/{len(decisions)} ({agree_count/len(decisions)*100:.0f}%)")


if __name__ == "__main__":
    main()
