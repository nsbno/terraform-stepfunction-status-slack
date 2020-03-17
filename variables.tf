variable "name_prefix" {
  description = "A prefix used for naming resources."
  type        = string
}

variable "artifact_bucket_name" {
  description = "The name of the bucket used for trigger files and artifacts"
  type = string
}

variable "slackwebhook" {
  description = "The slack webhook URL"
  type = string
}

variable "statestonotify" {
  description = "Sets the lambda to forward events based on values: all or errors"
  type = string
  default = "all"
}

variable "tags" {
  description = "A map of tags (key-value pairs) passed to resources."
  type        = map(string)
  default     = {}
}
