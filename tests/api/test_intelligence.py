from fastapi.testclient import TestClient

from market_intelligence.main import app

client = TestClient(app)


def test_analyze_endpoint_without_api_key() -> None:
    response = client.post(
        "/api/v1/intelligence/analyze",
        json={
            "symbol": "RELIANCE",
            "market": "NSE",
            "analysis_type": "fundamental",
            "include_news": True,
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["symbol"] == "RELIANCE"
    assert body["market_data"]["source"] == "mock"
    assert body["news"]
    assert body["report"]
