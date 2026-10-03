# Verificación de preparación

Comprobaciones realizadas durante la preparación del proyecto:

| Comprobación | Resultado |
|---|---|
| Pruebas unitarias/integración de backend | 19 aprobadas |
| Cobertura de líneas del backend | 100 % |
| Reservas concurrentes | Una respuesta 201 y otra 409 para la misma franja |
| Semgrep security-audit y reglas locales | 0 hallazgos; 109 reglas ejecutadas |
| pip-audit, dependencias de producción | 0 vulnerabilidades conocidas |
| Sintaxis JavaScript | Aprobada con node --check |
| Sintaxis Bash | Aprobada con bash -n |
| Parseo de workflows YAML | Aprobado para los seis workflows |
| Terraform fmt | Aprobado |
| Generación de documentación/OpenAPI | Aprobada |
| Terraform validate con proveedor Azure | No completado: el entorno impide crear el socket local del proveedor. infra.yml lo ejecuta en GitHub. |
| Prueba visual en navegador | No completada: navegador/descarga de navegador no disponibles en el entorno. Revisar en escritorio y móvil al publicar. |
| Construcción y escaneo Docker | Pendiente en GitHub; este entorno no tiene Docker |
| SonarQube Cloud | Pendiente de token, proyecto y ejecución real |
| Snyk | Pendiente de token, cuota y ejecución real |
| Despliegue Azure | Pendiente de configuración de la suscripción e identidad |

Estos resultados no equivalen a aprobación externa ni garantizan ausencia de vulnerabilidades futuras. La automatización bloquea el despliegue si los controles externos fallan. La evidencia válida para entregar será la ejecución real de GitHub Actions y las URLs publicadas.
