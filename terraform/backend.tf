terraform {
  backend "azurerm" {
    resource_group_name  = "rg-shopportal-tfstate"
    storage_account_name = "stshopportaltfstate2026"
    container_name       = "tfstate"
    key                  = "shopportal.tfstate"
    use_azuread_auth     = true
  }
}