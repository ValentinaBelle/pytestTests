import pytest
import requests
BASE_URL = 'your_sandbox_url' # https://sandbox.something.com/api/v3"
# Один url — все тесты используют. Меняешь в одном месте — меняется везде.

@pytest.fixture(scope="session") # один раз на всю сессию тестов
def api_session():
    session = requests.Session() # создаёт сессию - сохраняет cookies, заголовки, соединения между запросами.
    session.headers.update({
        "Content-Type": "application/json",
        "Accept": "application/json",
    })
    yield session
    session.close()


@pytest.fixture(scope="session")
def auth_headers(api_session): # получает токен один раз на сессию
    resp = api_session.post(f"{BASE_URL}/auth/token", json={ # POST-запрос словарь-JSON
        "client_id": "test_client",
        "client_secret": "test_secret",
        "grant_type": "client_credentials",
    })
    if resp.status_code != 200:
        pytest.skip(f"Auth failed: {resp.status_code} {resp.text}")
    token = resp.json().get("access_token")
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def payment_payload():
    return {
        "amount": 10000,  # 100
        "currency": "RUB",
        "card": {
            "number": "4111111111111111",
            "exp_month": "12",
            "exp_year": "2030",
            "cvv": "123",
            "holder": "IVAN IVANOV",
        },
        "capture": True,
        "description": "Test payment",
    }

def test_create_payment(api_session, auth_headers, payment_payload):
    resp = api_session.post(
        f"{BASE_URL}/payments",
        json=payment_payload,
        headers=auth_headers,
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["status"] in ("pending", "succeeded")
    assert data["amount"] == 10000
    assert data["currency"] == "RUB"
    assert "transaction_id" in data

# без токена
def test_create_no_auth(api_session, payment_payload):
    resp = api_session.post(f"{BASE_URL}/payments", json=payment_payload)
    assert resp.status_code == 401

# кривой токен
def test_create_invalid_token(api_session, payment_payload):
    headers = {"Authorization": "Bearer invalid_token_123"}
    resp = api_session.post(
        f"{BASE_URL}/payments", json=payment_payload, headers=headers
    )
    assert resp.status_code == 401

# не та валюта
def test_invalid_currency(api_session, auth_headers, payment_payload):
    payload = {**payment_payload, "currency": "USD"}
    resp = api_session.post(
        f"{BASE_URL}/payments", json=payload, headers=auth_headers
    )
    assert resp.status_code == 400

# не заполнено обязательное поле
def test_missing_required_field(api_session, auth_headers, payment_payload):
    payload = {k: v for k, v in payment_payload.items() if k != "amount"}
    resp = api_session.post(
        f"{BASE_URL}/payments", json=payload, headers=auth_headers
    )
    assert resp.status_code == 400