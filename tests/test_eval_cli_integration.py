import asyncio
import json
from pathlib import Path
import shutil

from app.eval import cli as eval_cli


class DummyEngine:
    async def retrieve(self, query: str, top_n: int, recall_top_k: int):
        return {"results": [{"doc_id": "1", "content": "alpha"}]}

    async def close(self) -> None:
        return None


def _write_jsonl(path: Path, rows):
    with path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")


def test_cli_integration_minimal(tmp_path, monkeypatch):
    data_path = tmp_path / "data.jsonl"
    _write_jsonl(
        data_path,
        [
            {"id": "1", "query": "q1", "relevant_doc_ids": ["1"]},
            {"id": "2", "query": "q2", "relevant_doc_ids": ["x"]},
        ],
    )

    config_path = tmp_path / "config.json"
    output_dir = Path("app/eval/outputs")
    if output_dir.exists():
        shutil.rmtree(output_dir)
    config_path.write_text(
        json.dumps(
            {
                "project": {"run_id": "test", "output_dir": str(output_dir)},
                "data": {"format": "jsonl", "path": str(data_path)},
                "engine": {"type": "api"},
                "api": {"base_url": "http://localhost:8010"},
                "runners": {"retrieval": {"enabled": True}},
                "report": {"formats": ["md", "json"], "save_samples": True},
            }
        ),
        encoding="utf-8",
    )

    monkeypatch.setattr(eval_cli, "build_engine", lambda config: DummyEngine())

    asyncio.run(eval_cli.run_eval(str(config_path)))

    report_path = output_dir / "report.md"
    assert report_path.exists()
    content = report_path.read_text(encoding="utf-8")
    assert "Eval Report" in content
