"""Pruebas de reglas de negocio y endpoints con una base temporal."""
import secrets
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import pytest
from fastapi.testclient import TestClient
from app.main import app, clock, minutes


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("DATABASE_PATH", str(tmp_path / "test.db"))
    monkeypatch.setenv("ADMIN_TOKEN", secrets.token_urlsafe(32))
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def admin_headers():
    import os
    return {"X-Admin-Token": os.environ["ADMIN_TOKEN"]}


@pytest.fixture
def user(client):
    response = client.post("/users", json={"name": "Ana López", "email": "ana@example.com"})
    assert response.status_code == 201
    return response.json()


def future_day():
    return (datetime.now(ZoneInfo("America/Lima")).date() + timedelta(days=2)).isoformat()


def request_body(user, **overrides):
    return {"court_id": 1, "user_id": user["id"], "date": future_day(),
            "time": "18:00", "duration": 60, "event": "Partido del equipo", **overrides}


def reserve(client, user, **overrides):
    return client.post("/rentals", json=request_body(user, **overrides),
                       headers={"X-User-Key": user["access_key"]})


def test_time_conversion():
    assert minutes("18:30") == 1110
    assert clock(1110) == "18:30"


def test_initial_courts_and_frontend(client):
    assert len(client.get("/courts").json()) == 3
    assert len(client.get("/courts/1").json()["schedules"]) == 7
    response = client.get("/")
    assert response.status_code == 200
    assert "CourtFlow" in response.text
    assert response.headers["x-content-type-options"] == "nosniff"
    assert client.get("/health").json() == {"status": "ok"}
    assert client.get("/courts/999").status_code == 404


def test_reservation_price_and_overlap(client, user):
    booking = reserve(client, user, duration=90)
    assert booking.status_code == 201
    assert booking.json()["total"] == 9000
    assert booking.json()["end_time"] == "19:30"
    assert booking.json()["status"] == "Pendiente"
    assert reserve(client, user, time="19:00").status_code == 409
    assert reserve(client, user, time="19:30").status_code == 201
    assert reserve(client, user, court_id=2).status_code == 201


@pytest.mark.parametrize("overrides", [
    {"duration": 0}, {"duration": 45}, {"duration": 300}, {"time": "25:00"},
    {"event": "a"}, {"court_id": -1}, {"date": "2020-01-01"},
])
def test_invalid_reservations(client, user, overrides):
    assert reserve(client, user, **overrides).status_code == 422


def test_closed_hours_and_unknown_court(client, user):
    assert reserve(client, user, time="07:00").status_code == 409
    assert reserve(client, user, time="22:30", duration=120).status_code == 409
    assert reserve(client, user, court_id=999).status_code == 404


def test_user_access_is_required(client, user):
    assert client.post("/rentals", json=request_body(user)).status_code == 401
    assert client.get(f"/users/{user['id']}/rentals").status_code == 401
    assert client.get("/users/999/rentals").status_code == 404


def test_availability_and_history(client, user):
    reserve(client, user)
    query = {"date": future_day(), "time": "18:00", "duration": 60}
    result = client.get("/courts/availability", params=query)
    assert result.status_code == 200
    assert result.json()[0]["available"] is False
    assert result.json()[1]["available"] is True
    history = client.get(f"/users/{user['id']}/rentals",
                         headers={"X-User-Key": user["access_key"]}).json()
    assert history[0]["court_name"] == "Loza Central"
    assert client.get("/courts/availability", params={**query, "duration": 45}).status_code == 422
    assert client.get("/courts/availability", params={**query, "date": "2020-01-01"}).status_code == 422


def test_admin_confirm_and_payment(client, user, admin_headers):
    booking = reserve(client, user).json()
    path = f"/rentals/{booking['id']}/confirm"
    assert client.post(path, json={"payment": "Pagado"}).status_code == 401
    response = client.post(path, json={"payment": "Pagado"}, headers=admin_headers)
    assert response.json()["status"] == "Confirmada"
    assert response.json()["payment"] == "Pagado"
    assert client.get("/rentals").status_code == 401
    assert len(client.get("/rentals?court_id=1", headers=admin_headers).json()) == 1
    assert client.get("/rentals?court_id=2", headers=admin_headers).json() == []
    assert client.post(f"/rentals/{booking['id']}/cancel",
                       headers={"X-User-Key": user["access_key"]}).status_code == 409


def test_cancel_releases_slot_and_cannot_confirm(client, user, admin_headers):
    booking = reserve(client, user).json()
    path = f"/rentals/{booking['id']}/cancel"
    assert client.post(path).status_code == 401
    assert client.post(path, headers={"X-User-Key": user["access_key"]}).status_code == 200
    assert reserve(client, user).status_code == 201
    assert client.post(f"/rentals/{booking['id']}/confirm",
                       json={"payment": "Pagado"}, headers=admin_headers).status_code == 409


def test_register_court_and_schedule(client, user, admin_headers):
    court = {"name": "Loza Nueva", "venue": "Sede Este", "sport": "Fútbol",
             "capacity": 12, "hourly_rate": 5000}
    assert client.post("/courts", json=court).status_code == 401
    response = client.post("/courts", json=court, headers=admin_headers)
    assert response.status_code == 201
    court_id = response.json()["id"]
    weekday = datetime.fromisoformat(future_day()).weekday()
    path = f"/courts/{court_id}/schedules"
    assert client.post(path, json={"weekday": weekday, "opens": "10:00", "closes": "09:00"},
                       headers=admin_headers).status_code == 422
    assert client.post(path, json={"weekday": weekday, "opens": "10:00", "closes": "20:00"},
                       headers=admin_headers).status_code == 200
    assert reserve(client, user, court_id=court_id, time="09:00").status_code == 409
    assert reserve(client, user, court_id=court_id).status_code == 201
    assert client.post(path, json={"weekday": weekday, "opens": "10:00", "closes": "17:00"},
                       headers=admin_headers).status_code == 409


def test_validation_rejects_bad_users_and_extra_fields(client):
    assert client.post("/users", json={"name": "A", "email": "bad"}).status_code == 422
    assert client.post("/users", json={"name": "Ana", "email": "a@example.com",
                                      "role": "admin"}).status_code == 422


def test_simultaneous_reservations_only_one_succeeds(client, user):
    with ThreadPoolExecutor(max_workers=2) as pool:
        statuses = list(pool.map(lambda _: reserve(client, user).status_code, range(2)))
    assert sorted(statuses) == [201, 409]


def test_missing_admin_configuration_fails_closed(tmp_path, monkeypatch):
    monkeypatch.setenv("DATABASE_PATH", str(tmp_path / "test.db"))
    monkeypatch.delenv("ADMIN_TOKEN", raising=False)
    with pytest.raises(RuntimeError, match="ADMIN_TOKEN"):
        with TestClient(app):
            pass
