"""Phase 4 tests: corpus accumulation, quality gates, fine-tuning stub."""

from __future__ import annotations

import json

import pytest

from training.data_accumulator import (
    corpus_stats,
    load_corpus,
    record_confirmed_session,
)
from training.finetune_pipeline import (
    run_finetuning,
    to_instruction_format,
    train_val_split,
)
from training.quality_checker import check_corpus, usable_entries


def _add(root, sid, *, mock=False, op="op1", sample="orders.csv",
         corrections=None, field="unit_cost", corrected="unit_cost"):
    record_confirmed_session(
        sid, mock_mode=mock, prompt_version="EXTRACTION_PROMPT_V1",
        raw_input_sample=sample,
        llm_response={"summary": {}},
        operator_corrections=corrections if corrections is not None else [
            {"field": field, "llm_predicted": "sales_price",
             "operator_corrected": corrected,
             "correction_type": "column_mapping"},
        ],
        final_clean_output={"stg_buyer_orders": 3},
        operator_id=op, root=root,
    )


def test_corpus_append_only_and_loadable(tmp_path):
    _add(tmp_path, "s1")
    _add(tmp_path, "s2")
    entries = load_corpus(tmp_path)
    assert [e["session_id"] for e in entries] == ["s1", "s2"]
    # gold-label shape preserved
    c = entries[0]["operator_corrections"][0]
    assert c["llm_predicted"] == "sales_price"
    assert c["operator_corrected"] == "unit_cost"
    assert c["correction_type"] == "column_mapping"


def test_corpus_pii_scrubbed(tmp_path):
    _add(tmp_path, "s1", sample="from jane@farm.com call 765-555-0100")
    raw = (tmp_path / "corpus_v1.jsonl").read_text()
    assert "jane@farm.com" not in raw
    assert "765-555-0100" not in raw


def test_mock_sessions_logged_but_excluded_from_training(tmp_path):
    _add(tmp_path, "real1", mock=False)
    _add(tmp_path, "mock1", mock=True)
    stats = corpus_stats(tmp_path)
    assert stats["total_sessions"] == 2
    assert stats["real_sessions"] == 1
    assert stats["mock_sessions"] == 1
    assert len(usable_entries(tmp_path)) == 1


def test_deduplication_same_input_same_operator(tmp_path):
    _add(tmp_path, "s1", sample="weekly.csv", op="op1")
    _add(tmp_path, "s2", sample="weekly.csv", op="op1")   # duplicate upload
    _add(tmp_path, "s3", sample="weekly.csv", op="op2")   # different operator
    rep = check_corpus(tmp_path)
    assert rep["duplicates_removed"] == 1
    assert rep["usable_sessions"] == 2


def test_label_conflict_detected_and_excluded(tmp_path):
    _add(tmp_path, "s1", sample="x.csv", field="price",
         corrected="unit_cost")
    _add(tmp_path, "s2", sample="y.csv", field="price",
         corrected="unit_cost")
    # same input as s1, same field, DIFFERENT label → conflict
    _add(tmp_path, "s3", sample="x.csv", field="price",
         corrected="sales_price")
    rep = check_corpus(tmp_path)
    assert rep["label_conflicts_excluded"] >= 1
    usable = usable_entries(tmp_path)
    assert all(e["raw_input_sample"] != "x.csv" for e in usable)


def test_finetuning_gate_blocks_under_50(tmp_path):
    for i in range(5):
        _add(tmp_path, f"s{i}", sample=f"f{i}.csv")
    with pytest.raises(NotImplementedError, match="requires >= 50"):
        run_finetuning(root=tmp_path)


def test_instruction_format_is_valid(tmp_path):
    _add(tmp_path, "s1", sample="orders_a.csv")
    _add(tmp_path, "s2", sample="orders_b.csv")
    examples = to_instruction_format(tmp_path,
                                     system_prompt="SYS")
    assert len(examples) == 2
    for ex in examples:
        assert set(ex) == {"system", "user", "assistant"}
        assert ex["system"] == "SYS"
        json.loads(ex["assistant"])   # assistant target is valid JSON


def test_split_stratified_by_operator(tmp_path):
    for i in range(8):
        _add(tmp_path, f"a{i}", sample=f"a{i}.csv", op="opA")
    for i in range(4):
        _add(tmp_path, f"b{i}", sample=f"b{i}.csv", op="opB")
    entries = usable_entries(tmp_path)
    examples = to_instruction_format(tmp_path, system_prompt="SYS")
    train, val = train_val_split(examples, entries=entries)
    assert len(train) + len(val) == len(examples)
    assert len(train) > len(val)


def test_class_imbalance_flagged(tmp_path):
    for i in range(10):
        _add(tmp_path, f"s{i}", sample=f"f{i}.csv",
             corrections=[{"field": "x", "llm_predicted": "a",
                           "operator_corrected": "b",
                           "correction_type": "column_mapping"}])
    rep = check_corpus(tmp_path)
    assert rep["class_imbalance_warning"] is not None
    assert "column_mapping" in rep["class_imbalance_warning"]


def test_corpus_stats_counts_toward_gate(tmp_path):
    _add(tmp_path, "s1", mock=False)
    stats = corpus_stats(tmp_path)
    assert stats["sessions_until_fine_tuning"] == 49
    assert stats["fine_tuning_threshold"] == 50
