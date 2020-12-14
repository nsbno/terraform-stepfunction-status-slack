provider "aws" {
  version = ">= 2.46"
  region  = "eu-west-1"
}

locals {
  name_prefix = "example"
  tags = {
    terraform = true
    project   = local.name_prefix
  }
}

module "slack-notifier" {
  source       = "../../"
  name_prefix  = local.name_prefix
  slackwebhook = "<slack-webhook-url>"
  tags         = var.tags
}
