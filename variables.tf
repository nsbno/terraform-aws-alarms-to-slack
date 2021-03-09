variable "name_prefix" {
  description = "A prefix used for naming resources."
  type        = string
}

variable "current_account_alias" {
  description = "An optional account alias to add to the Slack messages to make it easier to identify the the current account."
  default     = ""
}

variable "slack_webhook_url" {
  description = "A Slack webhook URL to post messages to."
  type        = string
}

variable "sns_topic_arns" {
  description = "A list of ARNs of SNS topics to forward messages from."
  default     = []
}

variable "lambda_timeout" {
  description = "The maximum number of seconds the Lambda is allowed to run."
  default     = 3
}

variable "tags" {
  description = "A map of tags (key-value pairs) passed to resources."
  type        = map(string)
  default     = {}
}
