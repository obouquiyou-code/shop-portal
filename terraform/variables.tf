variable "resource_group_name" {
  description = "Nom du Resource Group"
  type        = string
}

variable "location" {
  description = "Région Azure"
  type        = string
}

variable "app_service_plan_name" {
  description = "Nom de l'App Service Plan"
  type        = string
}

variable "webapp_name" {
  description = "Nom de la Web App"
  type        = string
}

variable "sql_server_name" {
  description = "Nom du serveur Azure SQL"
  type        = string
}

variable "sql_database_name" {
  description = "Nom de la base de données Azure SQL"
  type        = string
}

variable "sql_admin_login" {
  description = "Administrateur Azure SQL"
  type        = string
}

variable "sql_admin_password" {
  description = "Mot de passe administrateur Azure SQL"
  type        = string
  sensitive   = true
}