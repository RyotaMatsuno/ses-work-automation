"""Test 3: skill_utils unit tests"""
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from skill_utils import (
    normalize_skill,
    skill_match,
    normalize_skill_set,
    build_normalized_skill_set,
    has_skill_skip,
)


def test_normalize_skill():
    assert normalize_skill("Java") == "java"
    assert normalize_skill("  AWS  ") == "aws"
    assert normalize_skill("React.js") == "react.js"
    assert normalize_skill("") == ""
    assert normalize_skill(None) == ""
    print("test_normalize_skill: PASS")


def test_skill_match_exact():
    eng_set = normalize_skill_set(["Java", "Python", "AWS"])
    assert skill_match("Java", eng_set) is True
    assert skill_match("Go", eng_set) is False
    print("test_skill_match_exact: PASS")


def test_skill_match_alias():
    eng_set = normalize_skill_set(["react.js"])
    assert skill_match("React", eng_set) is True
    eng_set2 = normalize_skill_set(["django"])
    assert skill_match("Go", eng_set2) is False
    print("test_skill_match_alias: PASS")


def test_skill_match_pmo():
    eng_set = normalize_skill_set(["PMO"])
    assert skill_match("PMO", eng_set) is True
    print("test_skill_match_pmo: PASS")


def test_has_skill_skip():
    assert has_skill_skip("#skill_skip メモ") is True
    assert has_skill_skip("通常メモ") is False
    assert has_skill_skip(None) is False
    assert has_skill_skip("") is False
    print("test_has_skill_skip: PASS")


def test_normalize_skill_set():
    result = normalize_skill_set(["Java", "AWS", ""])
    assert "java" in result
    assert "aws" in result
    assert "" not in result
    print("test_normalize_skill_set: PASS")


def test_build_normalized_skill_set_alias():
    r1 = normalize_skill_set(["Java"])
    r2 = build_normalized_skill_set(["Java"])
    assert r1 == r2
    print("test_build_normalized_skill_set_alias: PASS")


if __name__ == "__main__":
    test_normalize_skill()
    test_skill_match_exact()
    test_skill_match_alias()
    test_skill_match_pmo()
    test_has_skill_skip()
    test_normalize_skill_set()
    test_build_normalized_skill_set_alias()
    print("\nAll skill_utils tests PASSED")
