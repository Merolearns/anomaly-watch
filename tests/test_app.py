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


def test_dashboard_rejects_unknown_dataset_name(client):
    # A crafted dataset name must not reach the filesystem: it falls back
    # to the default sample instead of building a path from user input.
    response = client.post("/", data={
        "dataset": "../../../etc/passwd", "window": "20", "threshold": "3.0",
        "pasted_csv": "",
    })
    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert "Unknown dataset" in html
    assert "Website traffic" in html


def test_dashboard_reports_bad_value_in_pasted_csv(client):
    # A non-numeric value mid-file is a typo, not a header: the dashboard
    # reports it instead of silently analyzing fewer points.
    response = client.post("/", data={
        "dataset": "website-traffic", "window": "20", "threshold": "3.0",
        "pasted_csv": "2026-01-01,100\n2026-01-02,101\n2026-01-03,abc\n",
    })
    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert "Could not load data" in html
    assert "not a number" in html
