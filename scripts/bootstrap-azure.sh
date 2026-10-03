#!/usr/bin/env bash
# Ejecutar UNA VEZ en Azure Cloud Shell (Bash), desde la raíz del repositorio.
set -euo pipefail
REPOSITORY="RobertoHCR/HUAMAN_EXAMEN_DE_UNIDAD_I_CALIDAD_Y_PRUEBAS_DE_SOFTWARE"
read -r -p "Región Azure [eastus]: " LOCATION
LOCATION="${LOCATION:-eastus}"
SUFFIX="$(python3 -c 'import secrets; print(secrets.token_hex(3))')"
PREFIX="huamancf${SUFFIX}"
RESOURCE_GROUP="rg-${PREFIX}"
STATE_ACCOUNT="cfstate${SUFFIX}"
SUBSCRIPTION_ID="$(az account show --query id -o tsv)"
TENANT_ID="$(az account show --query tenantId -o tsv)"
USER_OBJECT_ID="$(az ad signed-in-user show --query id -o tsv)"

for provider in Microsoft.Web Microsoft.ContainerRegistry Microsoft.ManagedIdentity Microsoft.Storage; do
  az provider register --namespace "$provider" --wait
done
az group create --name "$RESOURCE_GROUP" --location "$LOCATION" --output none
az storage account create --name "$STATE_ACCOUNT" --resource-group "$RESOURCE_GROUP" \
  --location "$LOCATION" --sku Standard_LRS --min-tls-version TLS1_2 \
  --allow-blob-public-access false --allow-shared-key-access false --output none
STORAGE_ID="$(az storage account show -g "$RESOURCE_GROUP" -n "$STATE_ACCOUNT" --query id -o tsv)"
RG_ID="/subscriptions/${SUBSCRIPTION_ID}/resourceGroups/${RESOURCE_GROUP}"
az role assignment create --assignee-object-id "$USER_OBJECT_ID" --assignee-principal-type User \
  --role "Storage Blob Data Contributor" --scope "$STORAGE_ID" --output none
CREATED=false
for attempt in $(seq 1 12); do
  if az storage container create --name tfstate --account-name "$STATE_ACCOUNT" \
    --auth-mode login --output none; then CREATED=true; break; fi
  sleep 10
done
if [[ "$CREATED" != true ]]; then
  echo "Espera la propagación del permiso y crea el contenedor tfstate con auth-mode login."
  exit 1
fi
APP_ID="$(az ad app create --display-name "github-${PREFIX}" --query appId -o tsv)"
SP_ID="$(az ad sp create --id "$APP_ID" --query id -o tsv)"
FREQUENT_CREDENTIAL="$(mktemp)"
python3 - "$REPOSITORY" "$FREQUENT_CREDENTIAL" <<'PY'
import json, sys
with open(sys.argv[2], "w", encoding="utf-8") as handle:
    json.dump({"name": "github-main", "issuer": "https://token.actions.githubusercontent.com",
               "subject": "repo:" + sys.argv[1] + ":ref:refs/heads/main",
               "audiences": ["api://AzureADTokenExchange"]}, handle)
PY
az ad app federated-credential create --id "$APP_ID" --parameters "$FREQUENT_CREDENTIAL" --output none
rm "$FREQUENT_CREDENTIAL"
for role in Contributor "Role Based Access Control Administrator"; do
  az role assignment create --assignee-object-id "$SP_ID" --assignee-principal-type ServicePrincipal \
    --role "$role" --scope "$RG_ID" --output none
done
az role assignment create --assignee-object-id "$SP_ID" --assignee-principal-type ServicePrincipal \
  --role "Storage Blob Data Contributor" --scope "$STORAGE_ID" --output none

cat > bootstrap-values.txt <<EOF
Configura estas VARIABLES en GitHub > Settings > Secrets and variables > Actions > Variables:
AZURE_CLIENT_ID=$APP_ID
AZURE_TENANT_ID=$TENANT_ID
AZURE_SUBSCRIPTION_ID=$SUBSCRIPTION_ID
AZURE_RESOURCE_GROUP=$RESOURCE_GROUP
AZURE_LOCATION=$LOCATION
AZURE_PREFIX=$PREFIX
TF_STATE_ACCOUNT=$STATE_ACCOUNT
TF_STATE_CONTAINER=tfstate
EOF
cat bootstrap-values.txt
echo "Ahora genera ADMIN_TOKEN y guárdalo sólo como secreto de GitHub."
echo "Después ejecuta infra y, cuando termine, deploy."
