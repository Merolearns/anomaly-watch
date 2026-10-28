import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from app import app


@pytest.fixture
def client():
    app.config["TESTING"] = True
    return app.test_client()


def test_dashboard_loads_and_contains_anomaly_row(client):
    response = client.get("/")
    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert "anomaly-row" in html
    # Default dataset (website-traffic) contains the injected spike.
    assert "2026-07-01" in html


def test_dashboard_post_with_controls(client):
    response = client.post("/", data={
        "dataset": "server-latency", "window": "10", "threshold": "3.0",
        "pasted_csv": "",
    })
    assert response.status_code == 200
    assert "2026-10-02 16:00" in response.get_data(as_text=True)


def test_api_returns_anomalies(client):
    response = client.post("/api/analyze", json={
        "values": [100, 101, 99, 100, 102, 100, 101, 99, 100, 101, 500],
        "window": 5, "threshold": 3.0,
    })
    assert response.status_code == 200
    body = response.get_json()
    assert body["summary"]["anomalies"] >= 1
    assert body["points"][-1]["is_anomaly"]


def test_api_rejects_bad_input(client):
    response = client.post("/api/analyze", json={"values": "not a list"})
    assert response.status_code == 400
    response = client.post("/api/analyze", json={})
    assert response.status_code == 400


def test_api_get_documents_usage(client):
    response = client.get("/api/analyze")
    assert response.status_code == 200
    assert "usage" in response.get_json()
