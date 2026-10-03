# Diccionario de datos

Fuente: app/schema.sql. Motor: SQLite.

## courts

| Campo | Tipo | Obligatorio | Clave | Descripción |
|---|---|---|---|---|
| id | INTEGER | Sí | PK | Identificador único. |
| name | TEXT | Sí |  | Name |
| venue | TEXT | Sí |  | Venue |
| sport | TEXT | Sí |  | Sport |
| capacity | INTEGER | Sí |  | Capacity |
| hourly_rate | INTEGER | Sí |  | Precio por hora en céntimos de sol. |

## rentals

| Campo | Tipo | Obligatorio | Clave | Descripción |
|---|---|---|---|---|
| id | INTEGER | Sí | PK | Identificador único. |
| court_id | INTEGER | Sí | FK → courts.id | Court id |
| user_id | INTEGER | Sí | FK → users.id | User id |
| date | TEXT | Sí |  | Fecha local del evento, ISO YYYY-MM-DD. |
| starts | INTEGER | Sí |  | Inicio, en minutos desde 00:00, hora de Perú. |
| ends | INTEGER | Sí |  | Fin exclusivo, en minutos desde 00:00, hora de Perú. |
| event | TEXT | Sí |  | Event |
| status | TEXT | Sí |  | Pendiente, Confirmada o Cancelada. Predeterminado: 'Pendiente'. |
| payment | TEXT | Sí |  | Pendiente o Pagado; registro manual por la sede. Predeterminado: 'Pendiente'. |
| total | INTEGER | Sí |  | Importe total en céntimos de sol, calculado por el backend. |
| created_at | TEXT | Sí |  | Marca de creación UTC generada por SQLite. Predeterminado: CURRENT_TIMESTAMP. |

## schedules

| Campo | Tipo | Obligatorio | Clave | Descripción |
|---|---|---|---|---|
| id | INTEGER | Sí | PK | Identificador único. |
| court_id | INTEGER | Sí | FK → courts.id | Court id |
| weekday | INTEGER | Sí |  | 0=Lunes, 6=Domingo. |
| opens | INTEGER | Sí |  | Apertura en minutos desde 00:00. |
| closes | INTEGER | Sí |  | Cierre en minutos desde 00:00. |

## users

| Campo | Tipo | Obligatorio | Clave | Descripción |
|---|---|---|---|---|
| id | INTEGER | Sí | PK | Identificador único. |
| name | TEXT | Sí |  | Name |
| email | TEXT | Sí |  | Email |
| access_hash | TEXT | Sí |  | SHA-256 de una clave aleatoria de acceso de 256 bits. |
