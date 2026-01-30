import json
from pathlib import Path

from app.eval.datasets import load_samples


def _write_jsonl(path: Path, rows):
    with path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")


def test_load_samples_jsonl_filters(tmp_path):
    data = [
        {"id": "1", "query": "q1", "relevant_doc_ids": ["a"], "split": "dev", "metadata": {"domain": "x"}},
        {"id": "2", "query": "q2", "relevant_doc_ids": ["b"], "split": "test", "metadata": {"domain": "y"}},
        {"id": "3", "query": "q3", "relevant_doc_ids": ["c"], "split": "dev", "metadata": {"domain": "x"}},
    ]
    path = tmp_path / "data.jsonl"
    _write_jsonl(path, data)

    samples = load_samples(
        path=str(path),
        format="jsonl",
        split="dev",
        filters={"domain": "x"},
        deduplicate=True,
        dedup_key="id",
    )
    assert len(samples) == 2
    assert all(s.split == "dev" for s in samples)


def test_load_samples_csv_list_fields(tmp_path):
    csv_path = tmp_path / "data.csv"
    csv_path.write_text(
        "id,query,answers,relevant_doc_ids\n"
        "1,q1,\"[\\\"a1\\\",\\\"a2\\\"]\",\"[\\\"d1\\\",\\\"d2\\\"]\"\n",
        encoding="utf-8",
    )
    samples = load_samples(path=str(csv_path), format="csv")
    assert len(samples) == 1
    assert samples[0].answers == ["a1", "a2"]
    assert samples[0].relevant_doc_ids == ["d1", "d2"]
