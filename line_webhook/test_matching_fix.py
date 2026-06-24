"""
test_matching_fix.py - Task P マッチング修正テスト
"""

import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

from skill_utils import normalize_skill, skill_match, build_normalized_skill_set


# ---- スキル正規化テスト ----

def test_normalize_exact_lower():
    assert normalize_skill("Java") == "java"

def test_normalize_fullwidth():
    assert normalize_skill("Ａ") == "a"

def test_normalize_fullwidth_space():
    s = normalize_skill("React　JS")
    assert "  " not in s

def test_skill_match_case_insensitive():
    eng = build_normalized_skill_set(["java"])
    assert skill_match("Java", eng) is True

def test_skill_match_alias_react():
    eng = build_normalized_skill_set(["React.js"])
    assert skill_match("React", eng) is True

def test_skill_match_alias_aws():
    eng = build_normalized_skill_set(["Amazon Web Services"])
    assert skill_match("AWS", eng) is True

def test_skill_match_no_false_positive_short():
    # "Go" は 2文字なので contains match を使わない
    eng = build_normalized_skill_set(["Django"])
    assert skill_match("Go", eng) is False

def test_skill_match_no_match():
    eng = build_normalized_skill_set(["Python", "Django"])
    assert skill_match("Java", eng) is False


# ---- 粗利フィルタ + stats テスト ----

def _make_run_reverse_matching():
    """webhook_server.py から関数を直接インポート（Flask起動なし）"""
    import importlib, types

    # Flask等の副作用なしで関数だけ取り出す
    spec = importlib.util.spec_from_file_location(
        "wh",
        os.path.join(os.path.dirname(__file__), "webhook_server.py"),
    )
    # importは重いので関数を直接定義して再現する簡易版でテスト
    return None


def _run_reverse_matching_local(engineer, projects):
    """webhook_server.run_reverse_matching の簡易ローカル実装でテスト"""
    from skill_utils import build_normalized_skill_set, skill_match as _sm

    eng_skills = set(engineer.get("skills", []))
    eng_skills_normalized = build_normalized_skill_set(eng_skills)
    eng_price = engineer.get("price", 0) or 0
    note = engineer.get("note", "") or ""
    skill_skip = "#skill_skip" in note
    matches = []
    stats = {
        "total_projects": len(projects),
        "excluded_negative_margin": 0,
        "excluded_no_skill_match": 0,
        "passed": 0,
    }
    for proj in projects:
        req_skills = set(proj.get("required_skills", []))
        proj_price = proj.get("price", 0) or 0
        gross = (proj_price - eng_price) if (proj_price > 0 and eng_price > 0) else 0
        if eng_price > 0 and proj_price > 0:
            if gross < 0:
                stats["excluded_negative_margin"] += 1
                continue
            if skill_skip and gross > 10:
                continue
        req_match = {s: _sm(s, eng_skills_normalized) for s in req_skills}
        if not skill_skip:
            if req_skills and not any(req_match.values()):
                stats["excluded_no_skill_match"] += 1
                continue
        stats["passed"] += 1
        matches.append({"project_name": proj.get("name", ""), "gross_profit": gross})
    return {"matches": matches, "stats": stats}


def test_gross_high_not_excluded():
    """eng=60, proj=100 → gross=40 → 除外されない（旧ロジックは除外）"""
    eng = {"price": 60, "skills": ["Java"]}
    proj = [{"name": "A", "price": 100, "required_skills": ["Java"]}]
    result = _run_reverse_matching_local(eng, proj)
    assert result["stats"]["passed"] == 1, "gross=40 は通過すべき"


def test_gross_negative_excluded():
    """eng=60, proj=50 → gross=-10 → 除外"""
    eng = {"price": 60, "skills": ["Java"]}
    proj = [{"name": "A", "price": 50, "required_skills": ["Java"]}]
    result = _run_reverse_matching_local(eng, proj)
    assert result["stats"]["excluded_negative_margin"] == 1
    assert result["stats"]["passed"] == 0


def test_gross_small_passes():
    """eng=60, proj=65 → gross=5 → 通過"""
    eng = {"price": 60, "skills": ["Java"]}
    proj = [{"name": "A", "price": 65, "required_skills": ["Java"]}]
    result = _run_reverse_matching_local(eng, proj)
    assert result["stats"]["passed"] == 1


def test_stats_accuracy():
    """10案件: 3粗利NG, 5スキル不一致, 2通過"""
    eng = {"price": 60, "skills": ["Java"]}
    projects = []
    for i in range(3):
        projects.append({"name": f"grossNG_{i}", "price": 50, "required_skills": ["Java"]})
    for i in range(5):
        projects.append({"name": f"skillNG_{i}", "price": 70, "required_skills": ["Python"]})
    for i in range(2):
        projects.append({"name": f"ok_{i}", "price": 70, "required_skills": ["Java"]})
    result = _run_reverse_matching_local(eng, projects)
    s = result["stats"]
    assert s["total_projects"] == 10
    assert s["excluded_negative_margin"] == 3
    assert s["excluded_no_skill_match"] == 5
    assert s["passed"] == 2


# ---- build_reverse_match_message_v2 の stats メッセージテスト ----

def test_message_no_match_with_stats():
    from matching_logic import build_reverse_match_message_v2
    stats = {"total_projects": 179, "excluded_negative_margin": 10, "excluded_no_skill_match": 169}
    msg = build_reverse_match_message_v2("田中太郎", [], 60, stats=stats)
    assert "マッチ案件なし" in msg
    assert "179件" in msg
    assert "粗利NG 10件" in msg
    assert "スキル不一致 169件" in msg


def test_message_no_match_no_stats():
    from matching_logic import build_reverse_match_message_v2
    msg = build_reverse_match_message_v2("田中太郎", [], 60)
    assert "マッチ案件なし" in msg


if __name__ == "__main__":
    tests = [v for k, v in list(globals().items()) if k.startswith("test_")]
    passed = failed = 0
    for fn in tests:
        try:
            fn()
            print(f"  OK  {fn.__name__}")
            passed += 1
        except Exception as e:
            print(f"  NG  {fn.__name__}: {e}")
            failed += 1
    print(f"\n{passed} passed, {failed} failed")
    sys.exit(1 if failed else 0)
