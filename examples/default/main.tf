terraform {
  required_version = ">= 0.12"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = ">= 2.46"
    }
  }
}

provider "aws" {
  region = "eu-west-1"
}

locals {
  name_prefix       = "example"
  slack_webhook_url = "<my-slack-webhook-url>"
  tags = {
    terraform   = true
    environment = "test"
  }
}

resource "aws_sns_topic" "this" {
  tags = local.tags
}

resource "aws_cloudwatch_metric_alarm" "this" {
  alarm_name                = "${local.name_prefix}-ec2"
  comparison_operator       = "GreaterThanOrEqualToThreshold"
  evaluation_periods        = "2"
  metric_name               = "CPUUtilization"
  namespace                 = "AWS/EC2"
  period                    = "120"
  statistic                 = "Average"
  threshold                 = "90"
  alarm_description         = "The CPU utilization on EC2 is high."
  ok_actions                = [aws_sns_topic.this.arn]
  alarm_actions             = [aws_sns_topic.this.arn]
  insufficient_data_actions = [aws_sns_topic.this.arn]
}


module "alarms" {
  source            = "../../"
  name_prefix       = local.name_prefix
  sns_topic_arns    = [aws_sns_topic.this.arn]
  slack_webhook_url = local.slack_webhook_url
  tags              = local.tags
}
