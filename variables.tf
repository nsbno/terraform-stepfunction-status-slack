variable "name_prefix" {
  description = "A prefix used for naming resources."
  type        = string
}

# This argument is not being used and should probably be removed in future updates
# Currently using a default value for it to ensure backwards-compatibility.
variable "artifact_bucket_name" {
  description = "The name of the bucket used for trigger files and artifacts"
  type        = string
  default     = ""
}

variable "slackwebhook" {
  description = "The slack webhook URL"
  type        = string
}

variable "statestonotify" {
  description = "Sets the lambda to forward events based on values: all or errors"
  type        = string
  default     = "all"
}

variable "tags" {
  description = "A map of tags (key-value pairs) passed to resources."
  type        = map(string)
  default     = {}
}

variable "lambda_timeout" {
  description = "The maximum number of seconds the Lambda is allowed to run"
  default     = 10
}


