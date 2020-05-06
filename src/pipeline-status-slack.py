import os
import logging
import json
import urllib
import boto3
from datetime import datetime
from urllib import request

logger = logging.getLogger()
logger.setLevel(logging.INFO)


def get_name_of_last_entered_state(event, events):
    """Backtracks to the last entered state of the execution and returns the name of it"""
    if event["type"].endswith("StateEntered"):
        return event["stateEnteredEventDetails"]["name"]
    previous_id = event["previousEventId"]
    previous_event = next((e for e in events if e["id"] == previous_id), None)
    if previous_event is None:
        return None
    return get_name_of_last_entered_state(previous_event, events)


def get_failed_message(execution_arn, client=None):
    """Returns a Markdown-formatted string describing what made the execution fail"""
    if client is None:
        client = boto3.client("stepfunctions")
    response = client.get_execution_history(
        executionArn=execution_arn, maxResults=500, reverseOrder=True
    )
    events = response["events"]
    failed_event = next(
        (event for event in events if event["type"] == "ExecutionFailed"), None
    )
    state_name = "Unknown state"
    cause = "Unknown"
    error_code = "Unknown error"
    if failed_event:
        state_name = get_name_of_last_entered_state(
            failed_event, events) or state_name
        cause = failed_event["executionFailedEventDetails"]["cause"]
        error_code = failed_event["executionFailedEventDetails"]["error"]
    return (
        f"*Status:* Failed in state `{state_name}`\n"
        f"*Error:* `{error_code}`\n"
        f"```{cause}```"
    )


def lambda_handler(event, context):
    logger.info(event)
    region = os.environ["AWS_REGION"]
    slack_webhook_url = os.environ["slackwebhook"]
    state_to_notify = os.environ["statestonotify"]

    status = event["detail"]["status"]

    state_machine_arn = event["detail"]["stateMachineArn"]
    state_machine_name = state_machine_arn.split(":")[6]
    execution_arn = event["detail"]["executionArn"]
    execution_name = execution_arn.split(":")[7]
    execution_url = f"https://console.aws.amazon.com/states/home?region={region}#/executions/details/{execution_arn}"

    timestamp = event["time"].split(".")[0]
    timestamp = datetime.strptime(timestamp[:-1], "%Y-%m-%dT%H:%M:%S")
    slack_message = [
        f"*Execution:* <{execution_url}|{execution_name}>",
        f"*Time:* {timestamp}"
    ]

    if status == 'RUNNING':
        slack_color = 'good'
        slack_message.append("*Status:* Started")
    elif status == 'SUCCEEDED':
        slack_color = 'good'
        slack_message.append("*Status:* Successfully finished")
    elif status == "FAILED":
        slack_color = 'danger'
        failed_message = get_failed_message(execution_arn)
        slack_message.append(failed_message)
    elif status == "ABORTED":
        slack_color = 'danger'
        slack_message.append('*Status:* Execution was manually aborted')
    elif status == "TIMED_OUT":
        slack_color = 'danger'
        slack_message.append('*Status:* Execution timed out')

    slack_attachment = {
        "attachments": [
            {
                "title": state_machine_name,
                "fallback": "fallback",
                "text": "\n".join(slack_message),
                "color": slack_color,
                "mrkdwn_in": ["text"],
            }
        ]
    }

    try:
        json_data = json.dumps(slack_attachment)
        logger.info("\nOutput " + str(json_data))
        if slack_color == "danger" or state_to_notify == "all":
            slack_request = urllib.request.Request(
                slack_webhook_url,
                data=json_data.encode("ascii"),
                headers={"Content-Type": "application/json"},
            )
            slack_response = urllib.request.urlopen(slack_request)
    except Exception as em:
        logger.exception("EXCEPTION: " + str(em))
