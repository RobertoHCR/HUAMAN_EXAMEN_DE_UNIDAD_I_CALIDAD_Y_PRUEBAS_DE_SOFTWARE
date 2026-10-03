# Guía de publicación — CourtFlow

El repositorio indicado ya existe. Falta subir el proyecto, conectar las cuentas y ejecutar las automatizaciones. Hazlo en este orden.

## 1. Subir el proyecto a GitHub

1. Descomprime el archivo del proyecto.
2. Abre https://github.com/RobertoHCR/HUAMAN_EXAMEN_DE_UNIDAD_I_CALIDAD_Y_PRUEBAS_DE_SOFTWARE.
3. Si está vacío, selecciona **uploading an existing file**. Si tiene archivos: **Add file → Upload files**.
4. Sube el contenido del proyecto, incluyendo la carpeta **.github**. En la raíz deben quedar README.md, Dockerfile, requirements.txt, app/, infra/, scripts/, tests/, docs/ y .github/.
5. Confirma el commit en la rama **main**.
6. Comprueba que existen **.github/workflows/infra.yml** y las otras automatizaciones.

Si la subida web omite .github o tienes Git instalado, usa PowerShell:

```powershell
git clone https://github.com/RobertoHCR/HUAMAN_EXAMEN_DE_UNIDAD_I_CALIDAD_Y_PRUEBAS_DE_SOFTWARE.git
cd HUAMAN_EXAMEN_DE_UNIDAD_I_CALIDAD_Y_PRUEBAS_DE_SOFTWARE
# Copia aquí todo el contenido del proyecto descomprimido, incluida .github.
git add .
git commit -m "Implementar CourtFlow y automatizaciones de calidad"
git branch -M main
git push -u origin main
```

Si Git solicita nombre/correo, configura tus datos con git config user.name y git config user.email. Inicia sesión con tu propia cuenta cuando GitHub lo solicite.

El primer push puede iniciar deploy y fallar porque todavía no hay variables/tokens. Es normal en la configuración inicial: al terminar los pasos siguientes ejecuta deploy manualmente.

**Verifica que el repositorio sea público** en Settings → General. No incluyas .env, claves, bases de datos ni estado Terraform.

## 2. Preparar Azure Student

1. Entra en https://portal.azure.com.
2. En **Subscriptions**, confirma que **Azure for Students** esté habilitada y revisa el saldo.
3. Abre **Cloud Shell** en modo **Bash**. Usa una sesión sin almacenamiento persistente si el portal ofrece esa opción; no necesitas crear una cuenta para guardar archivos de Cloud Shell.
4. Lista las suscripciones:

```bash
az account list -o table
az account set --subscription "ID_DE_AZURE_FOR_STUDENTS"
git clone https://github.com/RobertoHCR/HUAMAN_EXAMEN_DE_UNIDAD_I_CALIDAD_Y_PRUEBAS_DE_SOFTWARE.git
cd HUAMAN_EXAMEN_DE_UNIDAD_I_CALIDAD_Y_PRUEBAS_DE_SOFTWARE
bash scripts/bootstrap-azure.sh
```

5. El script pregunta la región; puedes probar eastus. Si Azure Student no permite crear B1 en esa región, elige una región permitida en tu suscripción. Elige la región antes de ejecutar infra.
6. Copia los valores que muestra el script. También quedan en bootstrap-values.txt, que no se sube al repositorio.

El script prepara el estado remoto y una identidad de GitHub con OIDC: no necesita almacenar una contraseña de Azure. Terraform creará el plan B1 Linux, App Service, Container Registry y la identidad que permite descargar la imagen.

**Costo:** B1, ACR Basic y almacenamiento consumen el crédito de Azure; no se afirma que sean gratuitos. Revisa Cost Management y crea un presupuesto. Un presupuesto avisa, no apaga los recursos. No es necesario contratar un dominio.

## 3. Agregar variables y secretos de GitHub

En tu repositorio: **Settings → Secrets and variables → Actions**.

En la pestaña **Variables → New repository variable**, agrega:

| Nombre | Valor |
|---|---|
| AZURE_CLIENT_ID | Lo mostrado por bootstrap |
| AZURE_TENANT_ID | Lo mostrado por bootstrap |
| AZURE_SUBSCRIPTION_ID | Lo mostrado por bootstrap |
| AZURE_RESOURCE_GROUP | Lo mostrado por bootstrap |
| AZURE_LOCATION | Región seleccionada |
| AZURE_PREFIX | Lo mostrado por bootstrap |
| TF_STATE_ACCOUNT | Lo mostrado por bootstrap |
| TF_STATE_CONTAINER | tfstate |
| SONAR_ORGANIZATION | Se obtiene en el paso 4 |
| SONAR_PROJECT_KEY | Se obtiene en el paso 4 |

Genera tu clave de administración en Cloud Shell:

```bash
python3 -c "import secrets; print(secrets.token_urlsafe(32))"
```

Guárdala en un gestor de contraseñas. En **Secrets → New repository secret**, agrega:

| Nombre | Valor |
|---|---|
| ADMIN_TOKEN | La clave aleatoria recién generada, de al menos 32 caracteres |
| SONAR_TOKEN | Se obtiene en el paso 4 |
| SNYK_TOKEN | Se obtiene en el paso 5 |

No pegues secretos en un archivo, commit, issue, captura o conversación. ADMIN_TOKEN también es la clave del panel Administración de la app.

## 4. Conectar SonarQube Cloud

1. Entra en https://sonarcloud.io e inicia sesión con GitHub.
2. Importa tu organización/cuenta de GitHub y este repositorio público.
3. Elige el plan disponible para proyectos públicos que permita análisis CI. Confirma los límites que indique tu cuenta.
4. Anota **Organization key** y **Project key** tal como los muestra Sonar.
5. En el proyecto, selecciona análisis con **GitHub Actions**. Desactiva **Automatic Analysis** si aparece habilitado, porque se usará el escaneo de CI.
6. En el perfil de tu cuenta, sección de seguridad/tokens, crea un token con acceso al proyecto.
7. Coloca SONAR_ORGANIZATION y SONAR_PROJECT_KEY en Variables, y SONAR_TOKEN en Secrets.

El workflow espera el quality gate y comprueba el proyecto completo. Si Sonar encuentra bugs, vulnerabilidades o hotspots, el workflow fallará y se guardará el reporte disponible. Corrige el código y vuelve a ejecutarlo.

El requisito es cero hotspots: marcarlos como revisados no satisface por sí solo esa condición; esta automatización comprueba el total de hotspots detectados.

## 5. Conectar Snyk

1. Entra en https://app.snyk.io y crea/inicia tu cuenta.
2. Confirma que tu organización tenga acceso a **Open Source** y **Container**, y cuota disponible.
3. En la configuración de tu cuenta, obtiene tu **API token**.
4. Agrégalo a GitHub como SNYK_TOKEN.

Semgrep se ejecuta sin cuenta. Snyk revisa dependencias e imagen; Semgrep analiza el código. Los informes se guardan incluso cuando se encuentran vulnerabilidades.

No se bajó el umbral a high ni se añadieron exclusiones para ocultar vulnerabilidades. Una imagen base puede incorporar hallazgos nuevos: revisa el reporte, actualiza la base/dependencias y repite el análisis. No prometas cero vulnerabilidades antes de obtener los reportes reales.

## 6. Ejecutar las automatizaciones

### Primero: infraestructura

En GitHub → **Actions → infra → Run workflow → main**.

- Espera que quede verde.
- En el resumen aparecerá la URL prevista del App Service.
- La aplicación todavía puede mostrar error porque su primera imagen aún no se ha publicado.

Si Terraform falla por región/cuota, revisa el mensaje y la disponibilidad de B1 en Azure Student. No vuelvas a ejecutar bootstrap si la identidad y el estado ya existen; corrige la configuración necesaria.

### Segundo: despliegue

En GitHub → **Actions → deploy → Run workflow → main**.

Ejecuta pruebas, Sonar, seguridad y documentación. Sólo si pasan todos publica la imagen escaneada y despliega.

- Descarga reports desde **Artifacts** al final de la ejecución.
- La URL definitiva aparece en el resumen de deploy.
- Una ejecución puede tardar varios minutos por los escaneos y el inicio del contenedor.
- Los próximos commits en main despliegan automáticamente después de los controles.

También puedes ejecutar sonar, snyk-semgrep y generase-documentation por separado para revisar resultados.

## 7. Comprobar la aplicación publicada

1. Abre https://TU_AZURE_PREFIX-web.azurewebsites.net.
2. Selecciona una fecha futura, hora, duración, deporte y sede.
3. Solicita una reserva con nombre, correo y evento.
4. En Mis reservas, comprueba fecha, precio y estado pendiente.
5. Vuelve a buscar esa franja: esa loza ya debe aparecer ocupada.
6. En Administración, introduce ADMIN_TOKEN.
7. Confirma el alquiler y registra el pago únicamente si lo estás demostrando como pago recibido por la sede.
8. Filtra el historial por loza, registra una loza y modifica un horario.
9. Revisa la interfaz desde un teléfono.
10. Prueba /health y la documentación interactiva /docs.

Los datos deben persistir al reiniciar el servicio y al publicar una nueva imagen. No escales a varias instancias: esta solución usa SQLite para mantener el examen sencillo.

## 8. Entregar la Pregunta 5

Completa ENTREGA.md y copia al examen:

```text
Aplicación publicada: https://TU_AZURE_PREFIX-web.azurewebsites.net
Repositorio: https://github.com/RobertoHCR/HUAMAN_EXAMEN_DE_UNIDAD_I_CALIDAD_Y_PRUEBAS_DE_SOFTWARE
Sonar: https://sonarcloud.io/project/overview?id=TU_SONAR_PROJECT_KEY
```

Sustituye los marcadores por las URLs reales. Guarda capturas de los workflows verdes, dashboard Sonar y reportes de seguridad. Conserva la aplicación disponible hasta la revisión del profesor.

## Problemas frecuentes

| Mensaje o síntoma | Qué revisar |
|---|---|
| AADSTS / No matching federated identity | El repositorio y rama main deben coincidir con la credencial federada; verifica los tres IDs de Azure. |
| AuthorizationFailed al crear recursos/asignar AcrPull | La identidad necesita Contributor y Role Based Access Control Administrator en el grupo del proyecto. |
| Terraform no accede a tfstate | Cuenta/contenedor correctos y rol Storage Blob Data Contributor; los permisos pueden tardar en propagarse. |
| No se puede registrar una app Entra | La cuenta/tenant restringe registros; usa un tenant donde tengas permiso o solicita al administrador el registro de la identidad. |
| Región restringida o cuota B1 insuficiente | Revisa las regiones permitidas y las cuotas de tu suscripción Student antes de cambiar AZURE_LOCATION. |
| Sonar project not found / not authorized | Project key, organization key, permisos del token y proyecto importado. |
| Sonar falla por hotspot | Revisa el archivo/línea y corrige el hallazgo. No inventes un informe limpio. |
| Snyk falla por cuota/producto | Cuenta y organización con Open Source/Container disponibles; examina la ejecución. |
| Snyk informa vulnerabilidad de imagen | Actualiza imagen base/paquetes con una versión corregida y vuelve a construir y escanear. |
| App Service muestra 503 | Revisa logs de contenedor, imagen publicada, AcrPull, puerto 8000 y ADMIN_TOKEN de 32+ caracteres. |
| Base de datos sin permisos | Confirma almacenamiento habilitado y DATABASE_PATH=/home/data/courtflow.db. |
| El workflow no aparece | La carpeta .github/workflows debe estar en la raíz del repositorio, rama main. |

Para logs del contenedor, ejecuta en Cloud Shell con tus valores:

```bash
az webapp log config --name "TU_PREFIX-web" --resource-group "TU_RESOURCE_GROUP" --docker-container-logging filesystem
az webapp log tail --name "TU_PREFIX-web" --resource-group "TU_RESOURCE_GROUP"
```

## Apagar y limpiar después de la evaluación

Detener únicamente la aplicación no elimina el costo del plan ni de ACR. Cuando el profesor termine la revisión, elimina el grupo de recursos del proyecto desde Azure Portal. Esto elimina aplicación, plan, registro, base persistente y estado Terraform: descarga primero cualquier dato que necesites conservar.

Elimina también la aplicación de Entra creada por bootstrap si ya no la utilizarás. No borres recursos de otros proyectos ni el grupo usado por tu examen anterior.
