# CourtFlow · Registro y alquiler de lozas deportivas

Proyecto del examen de Calidad y Pruebas de Software. Consulta disponibilidad por fecha, hora y duración; permite reservar lozas deportivas y administrar su alquiler.

## Tecnologías

- Backend: Python 3.12 y FastAPI.
- Frontend: HTML, CSS y JavaScript; diseño responsive, sin dependencias de interfaz.
- Base relacional: SQLite con claves foráneas, restricciones e índices.
- Contenedor: Docker, usuario sin privilegios.
- Nube: Azure App Service Linux, Azure Container Registry y Azure Storage para Terraform.
- Automatización: GitHub Actions, Terraform, SonarQube Cloud, Snyk y Semgrep.

Se usa Python en lugar de .NET conforme a la opción del enunciado que permite otro framework. Backend y frontend se publican juntos: una sola URL, sin CORS ni dos despliegues separados.

## Funcionalidades

- Registro de lozas por sede, deporte, capacidad y precio por hora.
- Disponibilidad semanal: un horario continuo por día.
- Filtros por deporte, sede, fecha, hora y duración.
- Reserva con validaciones en frontend y backend.
- Bloqueo transaccional de cruces, incluso para solicitudes simultáneas.
- Historial por usuario y por loza.
- Confirmación de alquiler y registro manual del pago desde administración.
- Cancelación de reservas sin pago para liberar la franja.
- Tres lozas de ejemplo; no hay reservas ficticias.

## Empezar

Sigue [GUIA-PASO-A-PASO.md](GUIA-PASO-A-PASO.md): subir archivos, conectar Azure, configurar Sonar/Snyk y ejecutar las automatizaciones.

### Ejecutar localmente

```bash
python -m venv .venv
# Windows PowerShell:
.venv\Scripts\Activate.ps1
# Linux/macOS: source .venv/bin/activate
pip install -r requirements-dev.txt
python -c "import secrets; print(secrets.token_urlsafe(32))"
# Copia la clave al comando siguiente (no la subas a GitHub).
# Windows PowerShell:
$env:ADMIN_TOKEN="TU_CLAVE_GENERADA"
# Linux/macOS: export ADMIN_TOKEN="TU_CLAVE_GENERADA"
uvicorn app.main:app --reload --port 8000
```

Abre http://localhost:8000. El panel Administración usa ADMIN_TOKEN. La base local se crea en data/courtflow.db.

### Docker

Copia .env.example a .env y completa ADMIN_TOKEN con una clave aleatoria. Ejecuta:

```bash
docker compose up --build
```

### Pruebas

```bash
python -m pytest --cov=app --cov-fail-under=90 --cov-report=xml
python scripts/generate_docs.py
```

Las pruebas cubren validación, acceso, disponibilidad, precios, cancelación, pago, configuración semanal y reservas concurrentes. La cobertura es del backend; no constituye prueba visual de la interfaz.

## Automatizaciones

| Archivo | Función |
|---|---|
| infra.yml | Aprovisiona Azure con Terraform y estado remoto. Ejecución manual inicial. |
| sonar.yml | Escanea, espera el quality gate y exige cero bugs, vulnerabilidades y hotspots del proyecto. Exporta JSON. |
| snyk-semgrep.yml | Escanea código, dependencias e imagen. Guarda informes y la imagen exacta analizada. |
| deploy.yml | En cada push a main o ejecución manual: pruebas, calidad, seguridad, documentación y luego despliegue. |
| generase-documentation.yml | Genera diccionario, diagramas Mermaid y OpenAPI. Se conserva el nombre exacto del enunciado. |
| tests.yml | Pruebas de integración y de reglas de negocio, con informe y cobertura. |

No se ignoran severidades bajas ni se continúa el despliegue con escaneos fallidos. La imagen que se despliega es la misma que se escaneó, transferida como artifact y etiquetada con el SHA del commit.

## API

| Método y ruta | Acceso / finalidad |
|---|---|
| POST /courts | Administrador: registrar loza. |
| GET /courts | Público: listar. |
| GET /courts/{id} | Público: detalle y horarios. |
| POST /courts/{id}/schedules | Administrador: día, apertura y cierre. |
| GET /courts/availability?date=YYYY-MM-DD&time=HH:MM&duration=60 | Público: disponibilidad de cada loza para esa franja. |
| POST /users | Crea acceso de usuario y entrega su clave una vez. |
| POST /rentals | Usuario: reserva; enviar X-User-Key. |
| POST /rentals/{id}/confirm | Administrador: confirmación y pago. |
| POST /rentals/{id}/cancel | Usuario propietario: cancelación sin pago. |
| GET /users/{id}/rentals | Usuario propietario: historial. |
| GET /rentals?court_id=1 | Administrador: historial general o por loza. |
| GET /health | Comprobación del servicio. |

Los endpoints de administración reciben X-Admin-Token. Documentación interactiva en /docs y contrato en /openapi.json.

## Alcance y datos

- Horarios en America/Lima. No se reservan eventos pasados ni se cruza a otro día.
- Duración: 30 a 240 minutos, en bloques de 30.
- Precios almacenados como enteros en céntimos: no hay errores de punto flotante al calcular.
- Una solicitud pendiente bloquea la franja hasta su cancelación; no hay expiración automática.
- Pago manual: no hay pasarela ni cobros electrónicos.
- El usuario recibe una clave aleatoria; el servidor conserva su hash y el navegador conserva el acceso. No hay contraseña, recuperación por email ni sincronización entre dispositivos.
- SQLite en /home/data se conserva al reiniciar o desplegar en App Service cuando el almacenamiento está habilitado. Usar una sola instancia; esta demo no pretende soportar escalado horizontal.
- Eliminar el App Service/grupo de recursos elimina sus datos. Para una aplicación con más carga o múltiples instancias, migrar a PostgreSQL o SQL Server.
- Terraform guarda valores sensibles en el estado remoto protegido por RBAC. No publicar estados, planes, .env, tokens ni bases de datos.

## Documentación y entrega

Consulta [docs/generated/diccionario-datos.md](docs/generated/diccionario-datos.md), [docs/generated/diagramas.md](docs/generated/diagramas.md) y [docs/MATRIZ-REQUISITOS.md](docs/MATRIZ-REQUISITOS.md).

Después de desplegar, completa [ENTREGA.md](ENTREGA.md) con las tres URLs reales. Los informes externos deben provenir de ejecuciones reales; el proyecto no incluye reportes aprobados ficticios.
