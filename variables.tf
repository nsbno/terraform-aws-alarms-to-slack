variable "name_prefix" {
  description = "A prefix used for naming resources."
  type        = string
}

variable "current_account_alias" {
  description = "An optional account alias to add to the Slack messages to make it easier to identify the current account."
  default     = ""
}

variable "slack_webhook_url" {
  description = "The default Slack webhook URLs to post messages to."
  type        = list(string)
}

variable "topic_webhook_overrides" {
  description = "An optional map of SNS topic ARNs and Slack webhook URLs to use instead of the default webhook (i.e., <arn>-[<url>] pairs)."
  type        = map(list(string))
  default     = {}
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
