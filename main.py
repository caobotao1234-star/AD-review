"""
广告合规审查 Agent - 批量运行入口

用法：
    python main.py [input_dir]

默认从 input/ 目录读取广告图片和商品 JSON 文件。
"""

import json
import sys
import os
from datetime import datetime
from pathlib import Path

from src.config import INPUT_DIR, OUTPUT_DIR, CONFIDENCE_THRESHOLD
from src.pairing import find_case_pairs, validate_batch
from src.agent import review_case
from src.confidence import evaluate_confidence, needs_human_review
from src.review_queue import write_to_review_queue
from src.audit_log import AuditLogger
from src.models import ReviewResult


def main(input_dir: str = None):
    """批量审查入口"""
    input_dir = input_dir or INPUT_DIR

    print("=" * 60)
    print("🔍 广告合规审查 Agent")
    print(f"   输入目录: {input_dir}")
    print(f"   置信度阈值: {CONFIDENCE_THRESHOLD}")
    print("=" * 60)

    # 1. 配对和验证
    pairs, errors = find_case_pairs(input_dir)
    pairs, batch_errors = validate_batch(pairs, errors)
    errors.extend(batch_errors)

    if errors:
        print(f"\n⚠️  发现 {len(errors)} 个问题:")
        for err in errors:
            print(f"   - {err}")

    if not pairs:
        print("\n❌ 没有有效的案例可处理")
        return

    print(f"\n📋 找到 {len(pairs)} 个有效案例")

    # 2. 逐个审查
    results: list[dict] = []
    review_count = 0

    for i, case in enumerate(pairs, 1):
        print(f"\n{'─' * 40}")
        print(f"📝 [{i}/{len(pairs)}] 审查案例: {case.case_id}")
        print(f"   用户: {case.product_data.get('user_id', 'unknown')}")
        print(f"   类目: {case.product_data.get('category', '未知')}")

        # 初始化审计日志
        logger = AuditLogger(case.case_id)

        # Agent 审查
        print("   🤖 Agent 推理中...")
        result_dict, steps = review_case(case)

        # 记录推理步骤到审计日志
        for step_num, step in enumerate(steps, 1):
            logger.log_step(
                step_type=step.get("role", "unknown"),
                content=step.get("content", ""),
                tool_name=step.get("tool_calls", [{}])[0].get("name") if step.get("tool_calls") else None,
                tool_input=step.get("tool_calls", [{}])[0].get("args") if step.get("tool_calls") else None,
            )

        # 置信度评估
        print("   🎯 置信度评估中...")
        evidence = json.dumps(result_dict, ensure_ascii=False)
        confidence, judge_a, judge_b = evaluate_confidence(evidence)

        logger.log_step(
            step_type="confidence_evaluation",
            content=f"置信度: {confidence}, 判断A: {json.dumps(judge_a, ensure_ascii=False)}, 判断B: {json.dumps(judge_b, ensure_ascii=False)}",
        )

        # 构建最终结果
        review_result = ReviewResult(
            case_id=case.case_id,
            user_id=case.product_data.get("user_id", "unknown"),
            violation_types=result_dict.get("violation_types", []),
            reasoning=result_dict.get("reasoning", ""),
            legal_references=result_dict.get("legal_references", []),
            confidence_score=confidence,
            recommended_action=result_dict.get("recommended_action", "通过"),
            image_path=case.image_path,
            json_path=case.json_path,
        )

        # 判断是否需要人工复核
        if needs_human_review(confidence):
            review_path = write_to_review_queue(review_result)
            review_count += 1
            print(f"   ⚡ 低置信度({confidence})，已加入复核队列")
            logger.log_step(step_type="human_review", content=f"写入复核队列: {review_path}")
        else:
            action_emoji = {"下架": "🚫", "限流": "⚠️", "标注": "📌", "通过": "✅"}.get(review_result.recommended_action, "❓")
            print(f"   {action_emoji} 结论: {review_result.recommended_action} (置信度: {confidence})")
            if review_result.violation_types:
                print(f"   违规类型: {', '.join(review_result.violation_types)}")

        # 记录最终判断
        logger.log_step(step_type="final_judgment", content=review_result.to_json())
        logger.save()

        results.append(review_result.to_dict())

    # 3. 输出结果
    Path(OUTPUT_DIR).mkdir(parents=True, exist_ok=True)
    output_path = os.path.join(OUTPUT_DIR, f"results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    # 4. 汇总
    print(f"\n{'=' * 60}")
    print(f"✅ 审查完成!")
    print(f"   总案例: {len(pairs)}")
    print(f"   结果文件: {output_path}")
    if review_count:
        print(f"   待复核: {review_count} 个案例 (见 review_queue/ 目录)")
    print("=" * 60)


if __name__ == "__main__":
    input_dir = sys.argv[1] if len(sys.argv) > 1 else None
    main(input_dir)
