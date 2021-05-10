data "aws_caller_identity" "this" {}
data "aws_region" "this" {}

locals {
  current_account_id = data.aws_caller_identity.this.account_id
  current_region     = data.aws_region.this.name
}


#######################################
#                                     #
# Slack SNS forwarder                 #
#                                     #
#######################################
data "archive_file" "this" {
  type        = "zip"
  source_file = "${path.module}/src/main.py"
  output_path = "${path.module}/.terraform_artifacts/package.zip"
}

resource "aws_lambda_function" "this" {
  function_name    = "${var.name_prefix}-sns-to-slack"
  role             = aws_iam_role.this.arn
  handler          = "main.lambda_handler"
  runtime          = "python3.8"
  timeout          = var.lambda_timeout
  filename         = data.archive_file.this.output_path
  source_code_hash = data.archive_file.this.output_base64sha256
  environment {
    variables = {
      CURRENT_ACCOUNT_ID    = local.current_account_id
      CURRENT_ACCOUNT_ALIAS = var.current_account_alias
      SLACK_WEBHOOK_URL     = var.slack_webhook_url
    }
  }
  tags = var.tags
}

resource "aws_iam_role" "this" {
  assume_role_policy = data.aws_iam_policy_document.lambda_assume.json
  tags               = var.tags
}

resource "aws_iam_role_policy" "logs_to_lambda" {
  policy = data.aws_iam_policy_document.logs_for_lambda.json
  role   = aws_iam_role.this.id
}

resource "aws_cloudwatch_log_group" "this" {
  name              = "/aws/lambda/${aws_lambda_function.this.function_name}"
  retention_in_days = 14
  tags              = var.tags
}

resource "aws_lambda_permission" "allow_sns" {
  count         = length(var.sns_topic_arns)
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.this.function_name
  principal     = "sns.amazonaws.com"
  source_arn    = var.sns_topic_arns[count.index]
}

resource "aws_sns_topic_subscription" "this" {
  count     = length(var.sns_topic_arns)
  topic_arn = var.sns_topic_arns[count.index]
  protocol  = "lambda"
  endpoint  = aws_lambda_function.this.arn
}
