"""API REST y frontend servidos desde un único contenedor."""
import hashlib
import hmac
import os
import secrets
from contextlib import asynccontextmanager
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Annotated
from zoneinfo import ZoneInfo

from fastapi import Depends, FastAPI, Header, HTTPException, Query
from fastapi.staticfiles import StaticFiles
from app.db import connection, initialize
from app.models import ConfirmationInput, CourtInput, RentalInput, ScheduleInput, UserInput

LOCAL_ZONE = ZoneInfo("America/Lima")
STATIC_PATH = Path(__file__).with_name("static")
TIME_PATTERN = r"^([01]\d|2[0-3]):[0-5]\d$"


@asynccontextmanager
async def lifespan(_app):
    if len(os.environ.get("ADMIN_TOKEN", "")) < 32:
        raise RuntimeError("ADMIN_TOKEN debe tener al menos 32 caracteres.")
    initialize()
    yield


app = FastAPI(title="CourtFlow API", version="1.0.0", lifespan=lifespan)


@app.middleware("http")
async def security_headers(request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; script-src 'self'; style-src 'self'; "
        "img-src 'self' data:; object-src 'none'; frame-ancestors 'none'; base-uri 'self'"
    )
    response.headers["Cache-Control"] = "no-store"
    return response


def admin(x_admin_token: Annotated[str | None, Header()] = None):
    expected = os.environ.get("ADMIN_TOKEN", "")
    if not expected or not x_admin_token or not hmac.compare_digest(expected, x_admin_token):
        raise HTTPException(401, "Clave de administración incorrecta.")


Admin = Annotated[None, Depends(admin)]


def minutes(value):
    hour, minute = map(int, value.split(":"))
    return hour * 60 + minute


def clock(value):
    return f"{value // 60:02d}:{value % 60:02d}"


def required(db, table, item_id):
    # Sólo tablas internas: nunca se interpola texto recibido por HTTP.
    queries = {
        "courts": "SELECT * FROM courts WHERE id=?",
        "users": "SELECT * FROM users WHERE id=?",
        "rentals": "SELECT * FROM rentals WHERE id=?",
    }
    row = db.execute(queries[table], (item_id,)).fetchone()
    if row is None:
        raise HTTPException(404, "Registro no encontrado.")
    return row


def verify_user(db, user_id, access_key):
    user = required(db, "users", user_id)
    digest = hashlib.sha256((access_key or "").encode()).hexdigest()
    if not hmac.compare_digest(digest, user["access_hash"]):
        raise HTTPException(401, "Acceso de usuario incorrecto.")


def validate_future(day, start):
    when = datetime.combine(day, datetime.min.time(), tzinfo=LOCAL_ZONE) + timedelta(minutes=start)
    if when <= datetime.now(LOCAL_ZONE):
        raise HTTPException(422, "Selecciona una fecha y hora futuras.")


def available(db, court_id, day, start, end):
    schedule = db.execute(
        "SELECT opens, closes FROM schedules WHERE court_id=? AND weekday=?",
        (court_id, day.weekday()),
    ).fetchone()
    if not schedule or start < schedule["opens"] or end > schedule["closes"]:
        return False
    return not db.execute(
        "SELECT 1 FROM rentals WHERE court_id=? AND date=? AND status!='Cancelada' "
        "AND starts < ? AND ends > ? LIMIT 1",
        (court_id, day.isoformat(), end, start),
    ).fetchone()


def rental_dict(row):
    item = dict(row)
    item["time"] = clock(item["starts"])
    item["end_time"] = clock(item["ends"])
    return item


@app.get("/health")
def health():
    with connection() as db:
        db.execute("SELECT 1").fetchone()
    return {"status": "ok"}


@app.get("/courts")
def list_courts():
    with connection() as db:
        return [dict(row) for row in db.execute("SELECT * FROM courts ORDER BY id")]


@app.post("/courts", status_code=201)
def create_court(body: CourtInput, _admin: Admin):
    with connection() as db:
        cursor = db.execute(
            "INSERT INTO courts(name,venue,sport,capacity,hourly_rate) VALUES(?,?,?,?,?)",
            (body.name, body.venue, body.sport, body.capacity, body.hourly_rate),
        )
        court_id = cursor.lastrowid
        db.executemany(
            "INSERT INTO schedules(court_id,weekday,opens,closes) VALUES(?,?,480,1380)",
            [(court_id, day) for day in range(7)],
        )
        return dict(required(db, "courts", court_id))


# La ruta fija debe ir antes que /courts/{court_id}.
@app.get("/courts/availability")
def availability(
    date: date,
    time: Annotated[str, Query(pattern=TIME_PATTERN)],
    duration: Annotated[int, Query(ge=30, le=240, multiple_of=30)] = 60,
):
    start = minutes(time)
    validate_future(date, start)
    with connection() as db:
        return [
            {**dict(row), "available": available(db, row["id"], date, start, start + duration)}
            for row in db.execute("SELECT * FROM courts ORDER BY id")
        ]


@app.get("/courts/{court_id}")
def court_detail(court_id: int):
    with connection() as db:
        court = dict(required(db, "courts", court_id))
        court["schedules"] = [
            {**dict(row), "opens": clock(row["opens"]), "closes": clock(row["closes"])}
            for row in db.execute(
                "SELECT weekday,opens,closes FROM schedules WHERE court_id=? ORDER BY weekday",
                (court_id,),
            )
        ]
        return court


@app.post("/courts/{court_id}/schedules")
def set_schedule(court_id: int, body: ScheduleInput, _admin: Admin):
    opens, closes = minutes(body.opens), minutes(body.closes)
    if closes <= opens:
        raise HTTPException(422, "El cierre debe ser posterior a la apertura.")
    with connection() as db:
        db.execute("BEGIN IMMEDIATE")
        required(db, "courts", court_id)
        bookings = db.execute(
            "SELECT date,starts,ends FROM rentals WHERE court_id=? AND date>=? AND status!='Cancelada'",
            (court_id, datetime.now(LOCAL_ZONE).date().isoformat()),
        )
        for row in bookings:
            if date.fromisoformat(row["date"]).weekday() == body.weekday:
                if row["starts"] < opens or row["ends"] > closes:
                    raise HTTPException(409, "Este horario dejaría una reserva fuera de disponibilidad.")
        db.execute(
            "INSERT INTO schedules(court_id,weekday,opens,closes) VALUES(?,?,?,?) "
            "ON CONFLICT(court_id,weekday) DO UPDATE SET opens=excluded.opens,closes=excluded.closes",
            (court_id, body.weekday, opens, closes),
        )
    return {"message": "Horario actualizado."}


@app.post("/users", status_code=201)
def create_user(body: UserInput):
    key = secrets.token_urlsafe(32)
    with connection() as db:
        cursor = db.execute(
            "INSERT INTO users(name,email,access_hash) VALUES(?,?,?)",
            (body.name, body.email, hashlib.sha256(key.encode()).hexdigest()),
        )
    return {"id": cursor.lastrowid, "name": body.name, "access_key": key}


@app.post("/rentals", status_code=201)
def create_rental(body: RentalInput, x_user_key: Annotated[str | None, Header()] = None):
    start, end = minutes(body.time), minutes(body.time) + body.duration
    validate_future(body.date, start)
    with connection() as db:
        # El bloqueo abarca comprobación e inserción: evita reservas concurrentes.
        db.execute("BEGIN IMMEDIATE")
        verify_user(db, body.user_id, x_user_key)
        court = required(db, "courts", body.court_id)
        if not available(db, body.court_id, body.date, start, end):
            raise HTTPException(409, "La loza no está disponible durante toda esa franja.")
        total = court["hourly_rate"] * body.duration // 60
        cursor = db.execute(
            "INSERT INTO rentals(court_id,user_id,date,starts,ends,event,total) VALUES(?,?,?,?,?,?,?)",
            (body.court_id, body.user_id, body.date.isoformat(), start, end, body.event, total),
        )
        return rental_dict(required(db, "rentals", cursor.lastrowid))


@app.get("/users/{user_id}/rentals")
def user_history(user_id: int, x_user_key: Annotated[str | None, Header()] = None):
    with connection() as db:
        verify_user(db, user_id, x_user_key)
        rows = db.execute(
            "SELECT r.*, c.name AS court_name, c.sport FROM rentals r "
            "JOIN courts c ON c.id=r.court_id WHERE r.user_id=? ORDER BY r.date DESC,r.starts DESC",
            (user_id,),
        )
        return [rental_dict(row) for row in rows]


@app.get("/rentals")
def admin_history(_admin: Admin, court_id: int | None = None):
    with connection() as db:
        rows = db.execute(
            "SELECT r.*,c.name AS court_name,c.sport,u.name AS user_name FROM rentals r "
            "JOIN courts c ON c.id=r.court_id JOIN users u ON u.id=r.user_id "
            "WHERE (? IS NULL OR r.court_id=?) ORDER BY r.date DESC,r.starts DESC",
            (court_id, court_id),
        )
        return [rental_dict(row) for row in rows]


@app.post("/rentals/{rental_id}/confirm")
def confirm(rental_id: int, body: ConfirmationInput, _admin: Admin):
    with connection() as db:
        db.execute("BEGIN IMMEDIATE")
        row = required(db, "rentals", rental_id)
        if row["status"] == "Cancelada":
            raise HTTPException(409, "Una reserva cancelada no se puede confirmar.")
        db.execute(
            "UPDATE rentals SET status='Confirmada',payment=? WHERE id=?",
            (body.payment, rental_id),
        )
        return rental_dict(required(db, "rentals", rental_id))


@app.post("/rentals/{rental_id}/cancel")
def cancel(rental_id: int, x_user_key: Annotated[str | None, Header()] = None):
    with connection() as db:
        db.execute("BEGIN IMMEDIATE")
        row = required(db, "rentals", rental_id)
        verify_user(db, row["user_id"], x_user_key)
        if row["payment"] == "Pagado":
            raise HTTPException(409, "Contacta con la sede para cancelar una reserva pagada.")
        db.execute("UPDATE rentals SET status='Cancelada' WHERE id=?", (rental_id,))
        return {"message": "Reserva cancelada."}


app.mount("/", StaticFiles(directory=STATIC_PATH, html=True), name="frontend")
