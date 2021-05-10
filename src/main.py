#!/usr/bin/env python
#
# Copyright (C) 2021 Vy
#
# Distributed under terms of the MIT license.

"""
Lambda function that forwards CloudWatch alarms to a Slack channel.
"""
import os
import logging
import json
import urllib.request
from datetime import datetime

logger = logging.getLogger()
logger.setLevel(logging.INFO)

INSUFFICIENT_DATA = "INSUFFICIENT_DATA"
ALARM = "ALARM"
OK = "OK"
FALLBACK = "FALLBACK"

STYLES = {
    FALLBACK: {"emoji": "❕"},
    INSUFFICIENT_DATA: {
        "color": "warning",
        "emoji": ":warning:",
    },
    ALARM: {
        "color": "danger",
        "emoji": ":rotating_light:",
    },
    OK: {
        "color": "good",
        "emoji": ":white_check_mark:",
    },
}


def parse_cloudwatch_alarm_event(record, account_meta={}):
    """Parse a CloudWatch alarm event and return a payload
    to be posted to Slack's webhook API"""
    subject = record["Sns"]["Subject"]
    cloudwatch_alarm = json.loads(record["Sns"]["Message"])
    alarm_timestamp = cloudwatch_alarm["StateChangeTime"]
    new_state_value = cloudwatch_alarm["NewStateValue"]
    old_state_value = cloudwatch_alarm["OldStateValue"]
    alarm_account_id = cloudwatch_alarm["AWSAccountId"]
    alarm_name = cloudwatch_alarm["AlarmName"]
    alarm_description = cloudwatch_alarm["AlarmDescription"]
    alarm_metric = cloudwatch_alarm["Trigger"].get("MetricName", None)
    if cloudwatch_alarm["Trigger"].get("MetricName", None):
        alarm_metric = f'`{cloudwatch_alarm["Trigger"]["Namespace"]}`/`{cloudwatch_alarm["Trigger"]["MetricName"]}`'
    else:
        alarm_metric = "Multiple metrics"
    account_information = alarm_account_id
    alarm_arn = cloudwatch_alarm["AlarmArn"]
    alarm_region = alarm_arn.split(":")[3]
    alarm_url = f"https://{alarm_region}.console.aws.amazon.com/cloudwatch/home?region={alarm_region}#alarmsV2:alarm/{alarm_name}!"
    if alarm_account_id == account_meta.get(
        "current_account_id", ""
    ) and account_meta.get("current_account_alias", ""):
        account_information = f"{account_information} (_{account_meta['current_account_alias']}_)"

    style = STYLES[new_state_value]
    try:
        parsed_timestamp = datetime.strptime(
            alarm_timestamp, "%Y-%m-%dT%H:%M:%S.%f+0000"
        )
    except ValueError:
        logger.warn("Failed to parse timestamp '%s'", alarm_timestamp)
        parsed_timestamp = None

    content = {
        "attachments": [
            {
                "pretext": f"{style['emoji']} CloudWatch Alarm changed state: `{old_state_value}` → `{new_state_value}`",
                "color": style["color"],
                "fields": [
                    {
                        "title": "Alarm",
                        "value": f"<{alarm_url}|{alarm_name}>",
                        "short": True,
                    },
                    {
                        "title": "Account",
                        "value": account_information,
                        "short": True,
                    },
                    {
                        "title": "Metric",
                        "value": alarm_metric,
                        "short": True,
                    },
                    {
                        "title": "Region",
                        "value": alarm_region,
                        "short": True,
                    },
                    {
                        "value": f"```{alarm_description}```",
                        "short": False,
                    },
                ],
                "mrkdwn_in": ["text", "value", "pretext"],
                "fallback": subject,
                **(
                    {"ts": int(parsed_timestamp.timestamp())}
                    if parsed_timestamp
                    else {"footer": alarm_timestamp}
                ),
            }
        ]
    }
    return content


def parse_general_event(record, account_meta={}):
    """Parse a general SNS message and return a payload
    to be posted to Slack's webhook API"""
    subject = record["Sns"]["Subject"]
    style = STYLES[FALLBACK]
    if "has exceeded your alert threshold" in subject:
        style = STYLES[ALARM]
    message = record["Sns"]["Message"]
    timestamp = record["Sns"]["Timestamp"]
    try:
        parsed_timestamp = datetime.strptime(
            timestamp, "%Y-%m-%dT%H:%M:%S.%fZ"
        )
    except ValueError:
        logger.warn("Failed to parse timestamp '%s'", parsed_timestamp)
        parsed_timestamp = None
    topic_arn = record["Sns"]["TopicArn"]
    *_, region, account_id, topic_name = topic_arn.split(":")
    url = f"https://{region}.console.aws.amazon.com/sns/v3/home?region={region}#/topic/{topic_arn}"
    account_information = account_id
    if account_meta.get(
        "current_account_id", ""
    ) == account_id and account_meta.get("current_account_alias", ""):
        account_information += f" (_{account_meta['current_account_alias']}_)"

    content = {
        "attachments": [
            {
                "pretext": f"{style['emoji']} {subject}",
                **(
                    {"color": style["color"]}
                    if style.get("color", None)
                    else {}
                ),
                "fields": [
                    {
                        "title": "SNS Topic",
                        "value": f"<{url}|{topic_name}>",
                        "short": True,
                    },
                    {
                        "title": "Account",
                        "value": account_information,
                        "short": True,
                    },
                    {
                        "value": f"```{message}```",
                        "short": False,
                    },
                ],
                "mrkdwn_in": ["text", "value", "pretext"],
                "fallback": subject,
                **(
                    {"ts": int(parsed_timestamp.timestamp())}
                    if parsed_timestamp
                    else {"footer": timestamp}
                ),
            }
        ]
    }
    return content


def get_slack_message_content(record, account_meta={}):
    """Return the payload to post to Slack"""
    try:
        message = json.loads(record["Sns"]["Message"])
        if message.get("AlarmName", ""):
            content = parse_cloudwatch_alarm_event(record, account_meta)
        else:
            content = parse_general_event(record, account_meta)
    except json.decoder.JSONDecodeError:
        # Not JSON
        content = parse_general_event(record, account_meta)
    return content


def lambda_handler(event, context):
    logger.info("Lambda received event '%s'", json.dumps(event))
    slack_webhook_url = os.environ["SLACK_WEBHOOK_URL"]
    current_account_id = os.environ["CURRENT_ACCOUNT_ID"]
    current_account_alias = os.environ["CURRENT_ACCOUNT_ALIAS"]

    account_meta = {
        "current_account_id": current_account_id,
        "current_account_alias": current_account_alias,
    }

    # There should only be one record
    record = event["Records"][0]
    content = get_slack_message_content(record, account_meta)
    data = json.dumps(content).encode("utf-8")

    try:
        slack_request = urllib.request.Request(
            slack_webhook_url,
            data=data,
            headers={"Content-Type": "application/json"},
        )
        urllib.request.urlopen(slack_request)
    except:
        logger.exception("Failed to post to Slack")
        raise
