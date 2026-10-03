terraform {
  required_version = ">= 1.9, < 2.0"
  required_providers {
    azurerm = { source = "hashicorp/azurerm", version = "~> 4.0" }
  }
  backend "azurerm" {}
}

provider "azurerm" {
  features {}
  resource_provider_registrations = "none"
}

variable "resource_group_name" { type = string }
variable "prefix" {
  type = string
  validation {
    condition     = can(regex("^[a-z][a-z0-9]{5,17}$", var.prefix))
    error_message = "Usa de 6 a 18 letras minúsculas o números, comenzando por una letra."
  }
}
variable "location" { type = string }
variable "admin_token" {
  type      = string
  sensitive = true
  validation {
    condition     = length(var.admin_token) >= 32
    error_message = "ADMIN_TOKEN debe tener al menos 32 caracteres."
  }
}

data "azurerm_resource_group" "app" { name = var.resource_group_name }

resource "azurerm_container_registry" "app" {
  name                = "${var.prefix}acr"
  resource_group_name = data.azurerm_resource_group.app.name
  location            = var.location
  sku                 = "Basic"
  admin_enabled       = false
}

resource "azurerm_service_plan" "app" {
  name                = "${var.prefix}-plan"
  resource_group_name = data.azurerm_resource_group.app.name
  location            = var.location
  os_type             = "Linux"
  sku_name            = "B1"
  worker_count        = 1
}

resource "azurerm_user_assigned_identity" "app" {
  name                = "${var.prefix}-identity"
  resource_group_name = data.azurerm_resource_group.app.name
  location            = var.location
}

resource "azurerm_role_assignment" "acr_pull" {
  scope                = azurerm_container_registry.app.id
  role_definition_name = "AcrPull"
  principal_id         = azurerm_user_assigned_identity.app.principal_id
}

resource "azurerm_linux_web_app" "app" {
  name                                           = "${var.prefix}-web"
  resource_group_name                            = data.azurerm_resource_group.app.name
  location                                       = var.location
  service_plan_id                                = azurerm_service_plan.app.id
  https_only                                     = true
  ftp_publish_basic_authentication_enabled       = false
  webdeploy_publish_basic_authentication_enabled = false
  identity {
    type         = "UserAssigned"
    identity_ids = [azurerm_user_assigned_identity.app.id]
  }
  site_config {
    always_on                                     = true
    minimum_tls_version                           = "1.2"
    ftps_state                                    = "Disabled"
    health_check_path                             = "/health"
    container_registry_use_managed_identity       = true
    container_registry_managed_identity_client_id = azurerm_user_assigned_identity.app.client_id
    application_stack {
      docker_image_name   = "courtflow:latest"
      docker_registry_url = "https://${azurerm_container_registry.app.login_server}"
    }
  }
  app_settings = {
    WEBSITES_PORT                       = "8000"
    WEBSITES_ENABLE_APP_SERVICE_STORAGE = "true"
    DATABASE_PATH                       = "/home/data/courtflow.db"
    ADMIN_TOKEN                         = var.admin_token
  }
  lifecycle {
    # deploy.yml fija una imagen por SHA; infra no revierte ese despliegue.
    ignore_changes = [site_config[0].application_stack[0].docker_image_name]
  }
  depends_on = [azurerm_role_assignment.acr_pull]
}

output "application_url" { value = "https://${azurerm_linux_web_app.app.default_hostname}" }
output "registry" { value = azurerm_container_registry.app.login_server }
output "web_app_name" { value = azurerm_linux_web_app.app.name }
