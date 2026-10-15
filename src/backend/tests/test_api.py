import os
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

needs_model = pytest.mark.skipif(
    not os.environ.get("LLM_API_KEY"),
    reason="local LLM endpoint not configured",
)

SAMPLE_CSV = """User ID,Time,Account,Operation,Coin,Change,Remark
1,2025-01-01 10:00:00,Spot,Deposit,EUR,200,
1,2025-01-01 10:00:05,Spot,Buy Crypto With Fiat,EUR,-200,
1,2025-01-01 10:00:10,Spot,Buy Crypto With Fiat,SOL,1.5,
"""


@pytest.fixture()
def client():
    from app.main import app

    with TestClient(app) as test_client:
        yield test_client


def test_health(client):
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_import_help(client):
    response = client.get("/api/import/help")
    data = response.json()
    assert len(data["steps"]) == 5
    assert "Transaction History" in data["steps"][1]


def test_csv_upload_imports_and_is_idempotent(client, tmp_path):
    csv_file = tmp_path / "Binance-Transaction-History.csv"
    csv_file.write_text(SAMPLE_CSV, encoding="utf-8")

    with csv_file.open("rb") as handle:
        first = client.post(
            "/api/import/csv",
            files={"file": ("Binance-Transaction-History.csv", handle, "text/csv")},
        )
    assert first.status_code == 200
    assert first.json()["summary"]["trades"] == 1

    with csv_file.open("rb") as handle:
        second = client.post(
            "/api/import/csv",
            files={"file": ("Binance-Transaction-History.csv", handle, "text/csv")},
        )
    assert second.status_code == 200

    from app.memory import MemoryStore
    from app.main import state

    positions = state["store"].get_positions()
    sol = next(p for p in positions if p.coin == "SOL")
    assert sol.avg_cost_usd == pytest.approx(200 * 1.10 / 1.5)


def test_csv_upload_rejects_non_csv(client):
    response = client.post(
        "/api/import/csv",
        files={"file": ("notes.txt", b"hello", "text/plain")},
    )
    assert response.status_code == 400


@needs_model
def test_chat_returns_signal(client):
    response = client.post(
        "/api/chat",
        json={"message": "Should I sell my SOL? Give me a signal.", "session_id": "test"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["content"]
    assert data["tools_used"]


@needs_model
def test_chat_session_persists(client):
    from app.main import state

    first = client.post("/api/chat", json={"message": "Hi", "session_id": "persist-test"})
    assert first.status_code == 200
    history = state["store"].get_chat_history("persist-test")
    assert history[0]["role"] == "user"
    assert history[-1]["role"] == "assistant"