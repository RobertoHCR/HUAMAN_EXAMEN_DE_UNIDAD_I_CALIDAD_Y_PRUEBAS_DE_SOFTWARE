PRAGMA foreign_keys = ON;
CREATE TABLE IF NOT EXISTS courts (
 id INTEGER PRIMARY KEY,
 name TEXT NOT NULL,
 venue TEXT NOT NULL,
 sport TEXT NOT NULL CHECK(sport IN ('Fútbol','Vóley','Básquet')),
 capacity INTEGER NOT NULL CHECK(capacity > 0),
 hourly_rate INTEGER NOT NULL CHECK(hourly_rate > 0)
);
CREATE TABLE IF NOT EXISTS users (
 id INTEGER PRIMARY KEY,
 name TEXT NOT NULL,
 email TEXT NOT NULL,
 access_hash TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS schedules (
 id INTEGER PRIMARY KEY,
 court_id INTEGER NOT NULL REFERENCES courts(id),
 weekday INTEGER NOT NULL CHECK(weekday BETWEEN 0 AND 6),
 opens INTEGER NOT NULL CHECK(opens >= 0),
 closes INTEGER NOT NULL CHECK(closes <= 1440 AND closes > opens),
 UNIQUE(court_id, weekday)
);
CREATE TABLE IF NOT EXISTS rentals (
 id INTEGER PRIMARY KEY,
 court_id INTEGER NOT NULL REFERENCES courts(id),
 user_id INTEGER NOT NULL REFERENCES users(id),
 date TEXT NOT NULL,
 starts INTEGER NOT NULL,
 ends INTEGER NOT NULL CHECK(ends > starts),
 event TEXT NOT NULL,
 status TEXT NOT NULL DEFAULT 'Pendiente' CHECK(status IN ('Pendiente','Confirmada','Cancelada')),
 payment TEXT NOT NULL DEFAULT 'Pendiente' CHECK(payment IN ('Pendiente','Pagado')),
 total INTEGER NOT NULL CHECK(total > 0),
 created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_rentals_court_date ON rentals(court_id, date);
CREATE INDEX IF NOT EXISTS idx_rentals_user ON rentals(user_id);
