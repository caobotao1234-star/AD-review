"""
本地快速验证脚本（不依赖 pytest，不依赖外部 API）

用法：
    python scripts/test_local.py
"""

import sys
import os
import json
import tempfile

project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from src.pairing import find_case_pairs, validate_batch
from src.tools.keywords import keyword_match
from src.tools.category import get_category_rules
from src.models import ReviewResult, ReviewQueueItem, AuditLogEntry
from src.audit_log import AuditLogger

passed = 0
failed = 0


def check(name, condition):
    global passed, failed
    if condition:
        print(f"  ✅ {name}")
        passed += 1
    else:
        print(f"  ❌ {name}")
        failed += 1


print("=" * 50)
print("本地逻辑验证")
print("=" * 50)

# --- 配对逻辑 ---
print("\n📁 配对逻辑测试")
with tempfile.TemporaryDirectory() as tmpdir:
    # 创建有效配对
    with open(os.path.join(tmpdir, "ad1.png"), "wb") as f:
        f.write(b"\x89PNG")
    with open(os.path.join(tmpdir, "ad1.json"), "w") as f:
        json.dump({"user_id": "u1"}, f)
    # 缺少 JSON
    with open(os.path.join(tmpdir, "ad2.jpg"), "wb") as f:
        f.write(b"\xff\xd8")

    pairs, errors = find_case_pairs(tmpdir)
    check("有效配对识别", len(pairs) == 1 and pairs[0].case_id == "ad1")
    check("缺失文件报告", len(errors) == 1 and "缺少 JSON" in errors[0])
    check("product_data 加载", pairs[0].product_data.get("user_id") == "u1")

# 批量限制
with tempfile.TemporaryDirectory() as tmpdir:
    for i in range(11):
        with open(os.path.join(tmpdir, f"x{i}.png"), "wb") as f:
            f.write(b"\x89PNG")
        with open(os.path.join(tmpdir, f"x{i}.json"), "w") as f:
            json.dump({}, f)
    pairs, errors = find_case_pairs(tmpdir)
    pairs, errors = validate_batch(pairs, errors)
    check("批量超限拒绝", len(pairs) == 0 and any("超限" in e for e in errors))

# --- 关键词检测 ---
print("\n🔑 关键词检测测试")
hits = keyword_match("这款产品全网最低价，根治失眠，央视推荐")
kws = [h.keyword for h in hits]
check("全网最低价 命中", "全网最低价" in kws)
check("根治 命中", "根治" in kws)
check("央视推荐 命中", "央视推荐" in kws)
check("违规类型正确", any(h.violation_type == "医疗暗示" for h in hits))
check("违规类型正确2", any(h.violation_type == "资质伪造" for h in hits))

hits_empty = keyword_match("普通商品描述，质量不错")
check("无违规文本无命中", len(hits_empty) == 0)

hits_pos = keyword_match("abc根治def")
check("位置正确", hits_pos[0].position == 3)

# --- 类目规则 ---
print("\n📋 类目规则测试")
rules = get_category_rules("医疗器械")
check("医疗器械规则加载", rules.severity_boost is True)
check("医疗器械禁止声明", "治愈" in rules.prohibited_claims)

rules_fin = get_category_rules("金融")
check("金融规则加载", "保本保息" in rules_fin.prohibited_claims)

rules_unknown = get_category_rules("随便什么")
check("未知类目降级", rules_unknown.severity_boost is False)

# --- 数据模型 ---
print("\n📦 数据模型测试")
r = ReviewResult(
    case_id="c1", user_id="u1",
    violation_types=["绝对化用语"],
    confidence_score=0.85,
    recommended_action="限流",
)
j = r.to_json()
parsed = json.loads(j)
check("ReviewResult 序列化", parsed["case_id"] == "c1")
check("ReviewResult 字段完整", all(k in parsed for k in ["case_id", "user_id", "violation_types", "reasoning", "legal_references", "confidence_score", "recommended_action"]))

r2 = ReviewResult.from_dict(parsed)
check("ReviewResult 反序列化", r2.case_id == "c1" and r2.confidence_score == 0.85)

item = ReviewQueueItem.from_review_result(r)
check("ReviewQueueItem 转换", item.human_decision is None and item.case_id == "c1")

# --- 审计日志 ---
print("\n📝 审计日志测试")
with tempfile.TemporaryDirectory() as tmpdir:
    # monkey-patch LOGS_DIR
    import src.audit_log as al
    original = al.LOGS_DIR
    al.LOGS_DIR = tmpdir

    logger = AuditLogger("test_case")
    logger.log_step(step_type="thought", content="开始分析")
    logger.log_step(step_type="action", tool_name="keyword_match", tool_input={"text": "test"})
    logger.log_step(step_type="final_judgment", content="通过")
    filepath = logger.save()

    check("日志文件创建", os.path.exists(filepath))
    with open(filepath, "r", encoding="utf-8") as f:
        log_data = json.load(f)
    check("日志步骤数正确", len(log_data) == 3)
    check("步骤编号递增", log_data[0]["step_number"] == 1 and log_data[2]["step_number"] == 3)
    check("最终判断记录", log_data[2]["step_type"] == "final_judgment")

    al.LOGS_DIR = original

# --- 汇总 ---
print(f"\n{'=' * 50}")
print(f"结果: {passed} 通过, {failed} 失败")
if failed == 0:
    print("🎉 全部通过!")
else:
    print("⚠️  有失败项，请检查")
    sys.exit(1)
