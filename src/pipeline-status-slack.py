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

    color = (
        "danger"
        if event["detail"]["status"] in ["FAILED", "ABORTED", "TIMED_OUT"]
        else "good"
    )

    # Send message to slack
    pipelinename = event["detail"]["stateMachineArn"]
    pipelinename = pipelinename.split(":")[6]
    executionarn = event["detail"]["executionArn"]
    executionname = executionarn.split(":")[7]
    execution_url = f"https://console.aws.amazon.com/states/home?region={region}#/executions/details/{executionarn}"

    message = []
    timestamp = event["time"].split(".")[0]
    timestamp = datetime.strptime(timestamp[:-1], "%Y-%m-%dT%H:%M:%S")
    message.append(f"*Execution:* <{execution_url}|{executionname}>")
    message.append("*Time:* " + str(timestamp))
    if event["detail"]["status"] == "RUNNING":
        message.append("*Status:* Started")
    elif event["detail"]["status"] == "SUCCEEDED":
        message.append("*Status:* Successfully finished")

    if color == "danger":
        failed_message = get_failed_message(executionarn)
        message.append(failed_message)

    slack_attachment = {
        "attachments": [
            {
                "title": pipelinename,
                "fallback": "fallback",
                "text": "\n".join(message),
                "color": color,
                "mrkdwn_in": ["text"],
            }
        ]
    }

    try:
        json_data = json.dumps(slack_attachment)
        logger.info("\nOutput " + str(json_data))
        if color == "danger" or state_to_notify == "all":
            slack_request = urllib.request.Request(
                slack_webhook_url,
                data=json_data.encode("ascii"),
                headers={"Content-Type": "application/json"},
            )
            slack_response = urllib.request.urlopen(slack_request)
    except Exception as em:
        logger.exception("EXCEPTION: " + str(em))
