"""Master Test Matrix registry — 8 dimensions / 42 modules (no silent omissions)."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Module:
    id: str
    dim: int
    name: str
    status: str  # GREEN | PARTIAL | GAP | N/A | STRETCH
    owners: tuple[str, ...] = ()


# Exactly 42 modules matching the Master Test Suite Plan.
MODULES: tuple[Module, ...] = (
    # --- Dim 1 preprocess ---
    Module("1.1a", 1, "E1 exact match", "GREEN", ("tests/master/test_dim1_e_repair.py",)),
    Module("1.1b", 1, "E2 homophone unique", "GREEN", ("tests/master/test_dim1_e_repair.py",)),
    Module("1.1c", 1, "E3 edit-distance-1", "GREEN", ("tests/master/test_dim1_e_repair.py",)),
    Module("1.1d", 1, "E4 delete-one typo", "GREEN", ("tests/master/test_dim1_e_repair.py",)),
    Module("1.1e", 1, "E5 never insert", "GREEN", ("tests/master/test_dim1_e_repair.py",)),
    Module("1.1f", 1, "user_dict F/H/emoji/oral", "GREEN", ("tests/test_preprocess.py",)),
    Module("1.2", 1, "F41–F50 dialect reorder", "GREEN", ("tests/test_preprocess.py",)),
    Module("1.3", 1, "G1–G10 quantity/time", "GREEN", ("tests/test_preprocess.py",)),
    Module("1.4", 1, "I social/poetry intercept", "GREEN", ("tests/test_preprocess.py",)),
    # --- Dim 2 decode ---
    Module("2.1", 2, "D1–D8 basic clauses", "GREEN", ("tests/test_design_kernel.py",)),
    Module("2.2", 2, "D9–D20 special Chinese", "GREEN", ("tests/test_design_kernel.py",)),
    Module(
        "2.3",
        2,
        "D21–D36 questions",
        "GREEN",
        ("tests/master/test_dim2_questions.py", "tests/test_design_kernel.py"),
    ),
    Module(
        "2.4",
        2,
        "D37–D46 compound",
        "GREEN",
        ("tests/master/test_dim2_compound_deixis.py", "tests/test_decode_robust.py"),
    ),
    Module(
        "2.5",
        2,
        "D47–D56 ellipsis/deixis",
        "GREEN",
        ("tests/master/test_dim2_compound_deixis.py", "tests/test_design_kernel.py"),
    ),
    Module("2.6", 2, "D57–D65 negation/modal", "GREEN", ("tests/test_design_kernel.py", "tests/test_decode_robust.py")),
    # --- Dim 3 memory ---
    Module("3.1", 3, "MEM1 focus_stack cap=5", "GREEN", ("tests/master/test_dim3_mem.py",)),
    Module("3.2", 3, "MEM2 durable vs session", "GREEN", ("tests/master/test_dim3_mem.py",)),
    Module("3.3", 3, "MEM3 session reset", "GREEN", ("tests/master/test_dim3_mem.py", "tests/test_design_kernel.py")),
    Module("3.4", 3, "MEM4 short-ask pin", "GREEN", ("tests/test_user_docs.py", "tests/test_d69_judge.py")),
    Module("3.5", 3, "MEM5 coref chain", "GREEN", ("tests/master/test_dim3_mem.py", "tests/test_decode_robust.py")),
    # --- Dim 4 content/D69 ---
    Module("4.1", 4, "D66 write content", "GREEN", ("tests/test_user_docs.py",)),
    Module("4.2", 4, "D67 read content", "GREEN", ("tests/test_user_docs.py",)),
    Module("4.3", 4, "D69 threshold/tier/ask", "GREEN", ("tests/test_d69_judge.py", "tests/test_labor_case.py")),
    Module("4.4", 4, "D69 also/enum/P2 surface", "GREEN", ("tests/test_d69_judge.py",)),
    Module("4.5", 4, "MULTI D67+D69", "GREEN", ("tests/test_d69_judge.py",)),
    # --- Dim 5 WC/QP ---
    Module("5.1", 5, "WC1 duplicate tell", "GREEN", ("tests/master/test_dim5_wc_qp.py",)),
    Module("5.2", 5, "WC2 contradictions coexist", "GREEN", ("tests/master/test_dim5_wc_qp.py",)),
    Module("5.3", 5, "WC3 exact drop", "GREEN", ("tests/master/test_dim5_wc_qp.py",)),
    Module("5.4", 5, "QP1 result priority", "GREEN", ("tests/test_design_kernel.py",)),
    Module("5.5", 5, "QP2/QP3 isa.trans + WH lock", "GREEN", ("tests/test_design_kernel.py",)),
    # --- Dim 6 REN ---
    Module("6.1", 6, "REN1 bare logic fallback", "GREEN", ("tests/test_design_kernel.py",)),
    Module("6.2", 6, "REN2 empty + reply_mode", "GREEN", ("tests/test_reply_mode.py",)),
    Module("6.3", 6, "judge_cite evidence split", "GREEN", ("tests/test_d69_judge.py",)),
    # --- Dim 7 robustness ---
    Module("7.1", 7, "unpunctuated multi-clause", "GREEN", ("tests/master/test_dim7_fuzz_smoke.py",)),
    Module("7.2", 7, "fuzz noise / huge number", "GREEN", ("tests/master/test_dim7_fuzz_smoke.py",)),
    Module("7.3", 7, "long text bounded", "GREEN", ("tests/master/test_dim7_fuzz_smoke.py",)),
    Module("7.4", 7, "ambig_mode clarify", "GREEN", ("tests/test_decode_robust.py",)),
    # --- Dim 8 domain/CI ---
    Module("8.1", 8, "multi user_dir isolation", "GREEN", ("tests/master/test_dim8_domain.py",)),
    Module("8.2", 8, "DecodeOutcome API contract", "GREEN", ("tests/test_decode_api.py",)),
    Module("8.3", 8, "eval_d69_100 gate", "GREEN", ("src/para/tools/eval_d69_100.py",)),
    Module("8.4", 8, "1000+ cases <1s", "GREEN", ("tests/master/test_dim8_stretch_smoke.py",)),
    Module("8.5", 8, "100k-turn leak check", "GREEN", ("tests/master/test_dim8_stretch_smoke.py",)),
)

assert len(MODULES) == 42, f"expected 42 modules, got {len(MODULES)}"


def by_status() -> dict[str, list[Module]]:
    out: dict[str, list[Module]] = {}
    for m in MODULES:
        out.setdefault(m.status, []).append(m)
    return out
