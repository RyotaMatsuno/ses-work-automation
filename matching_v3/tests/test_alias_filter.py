"""test_alias_filter.py — alias_filter.py のユニットテスト。"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOLS_DIR = ROOT / "tools"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))

from alias_filter import _apply_rules, _load_canonical_skills, _load_denylist

_DENYLIST = _load_denylist()
_CANONICAL_SKILLS = _load_canonical_skills()


def _chk(key: str, canonical: str, canonical_skills: frozenset[str] | None = None) -> str | None:
    code, _ = _apply_rules(key, canonical, _DENYLIST, canonical_skills or _CANONICAL_SKILLS)
    return code


def _not_pass(key: str, canonical: str) -> None:
    assert _chk(key, canonical) is not None


# ── R1 ────────────────────────────────────────────────────────

def test_r1_joshi_no():
    assert _chk("javaの経験者", "Java") == "R1"


def test_r1_joshi_wo():
    assert _chk("pythonを使った開発", "Python") == "R1"


def test_r1_conjunction_start():
    assert _chk("およびapi設計", "API") == "R1"


def test_r1_english_no_joshi_pass():
    assert _chk("javascript", "JavaScript") is None


# ── R2 ────────────────────────────────────────────────────────

def test_r2_jp_too_long():
    assert _chk("アプリケーションサーバー設定管理", "サーバ") == "R2"


def test_r2_space_too_many():
    assert _chk("aws lambda function handler", "Lambda") == "R2"


def test_r2_jp_short_pass():
    assert _chk("linux運用", "Linux") is None


# ── R3 ────────────────────────────────────────────────────────

def test_r3_noise_symbol_man():
    assert _chk("年収500万以上", "経験") == "R3"


def test_r3_noise_symbol_brackets():
    assert _chk("java【必須】", "Java") == "R3"


def test_r3_allowlist_vue3():
    assert _chk("vue3", "Vue.js") is None


def test_r3_allowlist_html5():
    assert _chk("html5", "HTML") is None


# ── R4 / R17 ──────────────────────────────────────────────────

def test_r4_danger_ai():
    assert _chk("aim", "AI") == "R4"


def test_r4_danger_aws():
    assert _chk("amazon cloud", "AWS") == "R4"


def test_r17_communication():
    assert _chk("高いコミュニケーション力", "コミュニケーション力") == "R4"


def test_r17_leader():
    assert _chk("チームリーダー", "リーダー") == "R4"


def test_r17_mail():
    assert _chk("ビジネスメール", "メール") == "R4"


def test_r17_execution():
    assert _chk("bpr企画 実行", "実行") == "R4"


# ── R5 ────────────────────────────────────────────────────────

def test_r5_aws_prefix():
    assert _chk("aws dynamodb", "DynamoDB") == "R5"


# ── R6 ────────────────────────────────────────────────────────

def test_r6_pmo():
    assert _chk("pmo", "PMO") == "R6"


# ── R9 ────────────────────────────────────────────────────────

def test_r9_allowlist_cplusplus():
    assert _chk("c++", "C++") is None


def test_r9_go_rejected():
    assert _chk("go", "Go") == "R9"


def test_r9_rpc_rejected():
    assert _chk("rpc", "gRPC") == "R9"


# ── R12: 短canonical / 先頭以外包含 ───────────────────────────

def test_r12_freshservice_se():
    _not_pass("freshservice", "SE")


def test_r12_superset_se():
    _not_pass("superset", "SE")


def test_r12_seo_se():
    _not_pass("seo対策", "SE")


def test_r12_googlespreadsheet_se():
    _not_pass("googlespredseet", "SE")


def test_r12_powerplatform_pl():
    _not_pass("powerplatform", "PL")


def test_r12_pl_slash_one():
    _not_pass("pl/1", "PL")


def test_r12_pl_slash_i():
    _not_pass("pl/i", "PL")


def test_r12_data_catalog_log():
    _not_pass("データカタログ", "ログ")


def test_r12_devexpress_express():
    assert _chk("devexpress", "Express") == "R12"


def test_r12_postgres_sql():
    assert _chk("postgres sql", "SQL") == "R12"


def test_r12_powerpages_rpa():
    assert _chk("powerpages", "RPA") == "R12"


def test_r12_google_go():
    assert _chk("google", "Go") == "R12"


def test_r12_pass_prefix_match():
    assert _chk("ansible運用保守", "Ansible") is None


def test_r12_pass_linux_unyo():
    assert _chk("linux運用保守", "Linux") is None


# ── R15: 括弧・カンマ ─────────────────────────────────────────

def test_r15_aws_paren():
    assert _chk("aws(dynamodb, sqs", "DynamoDB") == "R15"


def test_r15_excel_paren():
    assert _chk("excel(関数", "Excel") == "R15"


def test_r15_lambda_paren():
    assert _chk("lambda(python", "Lambda") == "R15"


def test_r15_genai_paren():
    assert _chk("生成ai(llm", "LLM") == "R15"


def test_r15_iac_paren():
    assert _chk("iac(ansible", "Ansible") == "R15"


# ── R16: 未登録canonical ──────────────────────────────────────

def test_r16_unknown_canonical():
  skills = frozenset(["Java", "Python"])
  assert _chk("somekey", "FakeCanonical", skills) == "R16"


# ── R13 / SKIP_EXP ────────────────────────────────────────────

def test_r13_boshu():
    assert _chk("python募集中", "Python") == "R13"


def test_skip_exp_keiken():
    assert _chk("ansible利用経験", "Ansible") == "SKIP_EXP"


# ── 通過ケース ────────────────────────────────────────────────

def test_pass_vue3():
    assert _chk("vue3", "Vue.js") is None


def test_pass_fastapi():
    assert _chk("fastapi", "FastAPI") is None


def test_pass_cobol_variant():
    assert _chk("cobol400", "COBOL") is None
