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

variable "state_machine_arns" {
  description = "An optional list of ARNs of AWS Step Functions state machines to report updates on. Default behavior is to report updates for all state machines in the current region."
  default     = []
  type        = list(string)
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

variable "report_failed_events_on_success" {
  description = "Whether to check for and report failed events found in the Step Functions execution despite a successful execution (e.g., a state failed, but the error was caught and successfully handled)."
  default     = false
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

variable "attention_on_failure" {
  description = "Add @here mention to Slack message on failure"
  type        = bool
  default     = false
}
