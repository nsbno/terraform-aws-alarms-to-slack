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

STYLES = {
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


def lambda_handler(event, context):
    logger.info("Lambda received event '%s'", json.dumps(event))
    slack_webhook_url = os.environ["SLACK_WEBHOOK_URL"]
    current_account_id = os.environ["CURRENT_ACCOUNT_ID"]
    current_account_alias = os.environ["CURRENT_ACCOUNT_ALIAS"]

    summary = event["Records"][0]["Sns"]["Subject"]
    cloudwatch_alarm = json.loads(event["Records"][0]["Sns"]["Message"])
    alarm_timestamp = cloudwatch_alarm["StateChangeTime"]
    new_state_value = cloudwatch_alarm["NewStateValue"]
    old_state_value = cloudwatch_alarm["OldStateValue"]
    alarm_account_id = cloudwatch_alarm["AWSAccountId"]
    alarm_name = cloudwatch_alarm["AlarmName"]
    alarm_description = cloudwatch_alarm["AlarmDescription"]
    alarm_metric = cloudwatch_alarm["Trigger"]["MetricName"]
    alarm_metric_namespace = cloudwatch_alarm["Trigger"]["Namespace"]
    account_information = alarm_account_id
    alarm_arn = cloudwatch_alarm["AlarmArn"]
    alarm_region = alarm_arn.split(":")[3]
    alarm_url = f"https://{alarm_region}.console.aws.amazon.com/cloudwatch/home?region={alarm_region}#alarmsV2:alarm/{alarm_name}!"
    if alarm_account_id == current_account_id and current_account_alias:
        account_information = (
            f"{account_information} (_{current_account_alias}_)"
        )

    style = STYLES[new_state_value]
    messages = [
        f"*{style['emoji']} {new_state_value}:* <{alarm_url}|{alarm_name}> in {alarm_region}",
        f"```{alarm_description}```",
    ]
    try:
        parsed_timestamp = datetime.strptime(
            alarm_timestamp, "%Y-%m-%dT%H:%M:%S.%f+0000"
        )
    except ValueError:
        logger.warn("Failed to parse timestamp '%s'", alarm_timestamp)
        parsed_timestamp = None

    content = json.dumps(
        {
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
                            "value": f"`{alarm_metric_namespace}`/`{alarm_metric}`",
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
                    "fallback": summary,
                    **(
                        {"ts": int(parsed_timestamp.timestamp())}
                        if parsed_timestamp
                        else {"footer": alarm_timestamp}
                    ),
                }
            ]
        }
    )

    try:
        slack_request = urllib.request.Request(
            slack_webhook_url,
            data=content.encode("utf-8"),
            headers={"Content-Type": "application/json"},
        )
        urllib.request.urlopen(slack_request)
    except:
        logger.exception("Failed to post to Slack")
        raise
