"""Tests for ``scripts/run_auction_book.py`` in shadow mode: where the budget
comes from, the shadow book carried from the evening to the morning, and the
refusals. Nothing here connects to a broker."""

from __future__ import annotations

import importlib.util
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import ModuleType
from typing import Any
from zoneinfo import ZoneInfo

import pytest

SCRIPT = Path(__file__).resolve().parents[3] / "scripts" / "run_auction_book.py"
NEW_YORK = ZoneInfo("America/New_York")


@pytest.fixture(scope="module")
def runner() -> ModuleType:
    spec = importlib.util.spec_from_file_location("run_auction_book", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module  # dataclasses look their module up while it is executed
    spec.loader.exec_module(module)
    return module


def _write(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")


def _targets(book: str, decided_at: datetime) -> dict[str, Any]:
    return {
        "schema": 1,
        "book_id": book,
        "trade_date": decided_at.astimezone(NEW_YORK).date().isoformat(),
        "decided_at": decided_at.isoformat(),
        "targets": [
            {"symbol": "AAA", "venue": "XNAS", "weight": 0.5, "reference_price": 100.0},
            {"symbol": "BBB", "venue": "XNYS", "weight": 0.5, "reference_price": 40.0},
        ],
    }


def _records(book_dir: Path) -> list[dict[str, Any]]:
    lines = (book_dir / "runs.jsonl").read_text(encoding="utf-8").splitlines()
    return [json.loads(line) for line in lines]


def _args(tmp_path: Path, phase: str, *more: str) -> list[str]:
    return ["--phase", phase, "--book", "b1", "--data-dir", str(tmp_path), *more]


def test_shadow_enter_then_exit_carries_the_shadow_book(
    runner: ModuleType, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    book_dir = tmp_path / "b1"
    _write(book_dir / "settings.json", {"budget_usd": 10000})
    _write(book_dir / "targets.json", _targets("b1", datetime.now(timezone.utc)))

    assert runner.main(_args(tmp_path, "enter", "--skip-time-checks")) == runner.DONE
    out = capsys.readouterr().out
    assert "BUY      50 AAA" in out and "BUY     125 BBB" in out and "MOC/DAY" in out
    assert "10,000.00 USD of 10,000.00" in out
    assert not (book_dir / "state.json").exists()  # the real book is untouched by a shadow run
    held = json.loads((book_dir / "state.shadow.json").read_text(encoding="utf-8"))
    assert [(h["symbol"], h["shares"]) for h in held["holdings"]] == [("AAA", 50), ("BBB", 125)]

    assert runner.main(_args(tmp_path, "exit", "--skip-time-checks")) == runner.DONE
    out = capsys.readouterr().out
    assert "SELL     50 AAA" in out and "SELL    125 BBB" in out and "MKT/OPG" in out
    assert (
        json.loads((book_dir / "state.shadow.json").read_text(encoding="utf-8"))["holdings"] == []
    )

    assert runner.main(_args(tmp_path, "exit", "--skip-time-checks")) == runner.DONE
    assert "nothing to sell" in capsys.readouterr().out
    log = _records(book_dir)
    assert [(r["phase"], r["mode"], len(r["orders"])) for r in log] == [
        ("enter", "shadow", 2),
        ("exit", "shadow", 2),
        ("exit", "shadow", 0),
    ]


def test_command_line_overrides_the_settings_file(
    runner: ModuleType, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    book_dir = tmp_path / "b1"
    _write(book_dir / "settings.json", {"budget_usd": 10000})
    _write(book_dir / "targets.json", _targets("b1", datetime.now(timezone.utc)))
    code = runner.main(_args(tmp_path, "enter", "--skip-time-checks", "--budget-usd", "2000"))
    assert code == runner.DONE and "BUY      10 AAA" in capsys.readouterr().out
    code = runner.main(_args(tmp_path, "enter", "--skip-time-checks", "--max-names", "1"))
    assert code == runner.REFUSED and "limit of 1" in capsys.readouterr().out


def test_enter_needs_a_budget_a_targets_file_and_valid_settings(
    runner: ModuleType, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    book_dir = tmp_path / "b1"
    assert runner.main(_args(tmp_path, "enter", "--skip-time-checks")) == runner.BAD_INPUT
    assert "no budget" in capsys.readouterr().out
    _write(book_dir / "settings.json", {"budget_usd": 10000})
    assert (
        runner.main(_args(tmp_path, "enter", "--skip-time-checks")) == runner.BAD_INPUT
    )  # no targets
    capsys.readouterr()
    _write(book_dir / "settings.json", {"budgett_usd": 10000})
    assert runner.main(_args(tmp_path, "enter", "--skip-time-checks")) == runner.BAD_INPUT
    assert "unknown keys" in capsys.readouterr().out
    assert runner.main(_args(tmp_path, "enter", "--send", "--skip-time-checks")) == runner.BAD_INPUT


def test_enter_refuses_stale_or_foreign_targets_and_logs_why(
    runner: ModuleType, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    book_dir = tmp_path / "b1"
    _write(book_dir / "settings.json", {"budget_usd": 10000})
    _write(
        book_dir / "targets.json", _targets("b1", datetime.now(timezone.utc) - timedelta(days=3))
    )
    assert runner.main(_args(tmp_path, "enter")) == runner.REFUSED  # time checks on
    assert "REFUSED: targets are for" in capsys.readouterr().out
    _write(book_dir / "targets.json", _targets("someone-else", datetime.now(timezone.utc)))
    assert runner.main(_args(tmp_path, "enter", "--skip-time-checks")) == runner.REFUSED
    assert "not 'b1'" in capsys.readouterr().out
    assert [("refused" in r) for r in _records(book_dir)] == [True, True]
    assert not (book_dir / "state.shadow.json").exists()  # a refusal changes nothing
