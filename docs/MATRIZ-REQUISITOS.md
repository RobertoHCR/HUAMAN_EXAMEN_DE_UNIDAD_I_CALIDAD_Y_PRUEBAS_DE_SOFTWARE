# Matriz de requisitos y evidencias

| Requisito | Implementación | Evidencia |
|---|---|---|
| Aplicación y validaciones frontend/backend (2) | FastAPI, formularios HTML, Pydantic y reglas del servidor | app/, tests/, aplicación publicada |
| Repositorio GitHub | Repositorio público indicado por el alumno | URL del repositorio |
| Imagen de contenedor backend (1) | Dockerfile; imagen publicada en ACR | deploy, registro ACR |
| Terraform e infra.yml (2) | infra/main.tf, estado en Azure Storage | ejecución infra y recursos Azure |
| sonar.yml sin bugs, vulnerabilidades/hotspots (2) | Gate y comprobación de totales de Sonar | sonar-report y URL Sonar |
| snyk-semgrep.yml, código e imagen sin vulnerabilidades (2) | Semgrep, Snyk dependencias, Snyk Container | security-reports |
| deploy.yml (2) | Cadena de validación, imagen escaneada, despliegue App Service | ejecución deploy |
| Diccionario, ER, clases, componentes y despliegue Mermaid (3) | generate_docs.py deriva esquema/modelos y compone arquitectura | application-documentation y docs/generated |
| Disponibilidad semanal | schedules, weekday, apertura/cierre | panel Administración y detalle de loza |
| Historial usuario/loza | Historial propio y filtro por loza en administración | GET /users/{id}/rentals y GET /rentals?court_id= |
| Confirmación y pago | Estado de alquiler y registro manual de pago | panel Administración |
| Unitarias e integración | Conversión de horas y reglas mediante TestClient/SQLite temporal | tests-and-coverage |
