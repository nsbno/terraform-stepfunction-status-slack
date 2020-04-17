import os
import logging
import json
import urllib
import boto3
from datetime import datetime
from urllib import request

logger = logging.getLogger()
formatter = logging.Formatter('%(asctime)s %(levelname)s %(name)s %(message)s', '%Y-%m-%d %H:%M:%S')
for h in logger.handlers:
    h.setFormatter(formatter)
logger.setLevel(logging.INFO)


def lambda_handler(event, context):
    logger.info(event)
    slack_webhook_url = os.environ['slackwebhook']
    state_to_notify = os.environ['statestonotify']

    color = "danger" if event['detail']['status'] in ["FAILED", "ABORTED", "TIMED_OUT"] else "good"

    # Send message to slack
    pipelinename = event['detail']['stateMachineArn']
    pipelinename = pipelinename.split(":")[6]
    executionarn = event['detail']['executionArn']
    executionname = executionarn.split(":")[7]

    message = []
    timestamp = event['time'].split(".")[0]
    timestamp = datetime.strptime(timestamp[:-1], '%Y-%m-%dT%H:%M:%S')
    message.append("*Execution:* " + executionname)
    message.append("*Time:* " + str(timestamp))
    if event['detail']['status'] == "RUNNING":
        message.append("*Status:* Started")
    elif event['detail']['status'] == "SUCCEEDED":
        message.append("*Status:* Successfully finished")

    if (color == "danger"):
        client = boto3.client("stepfunctions")
        output = client.get_execution_history(executionArn=executionarn)
        logger.info('\nFailed ' + str(output))

        try:
            for eventer in output["events"]:
                if ("ExecutionFailed" in eventer["type"]):
                    cause = "```" + str(eventer["executionFailedEventDetails"]["cause"]) + "```"
                    error_code = str(eventer["executionFailedEventDetails"]["error"])

        except Exception:
            logger.exception('Something went wrong when parsing execution details')
            cause = 'Unknown'
            error_code = 'Unknown error'
        message.append(f"*Status:* Failed\n*Error:* {error_code}\n" + cause)

    slack_attachment = {
        "attachments": [
            {
                "title": pipelinename,
                "fallback": "fallback",
                "text": "\n".join(message),
                "color": color,
                "mrkdwn_in": [
                    "text"
                ]
            }
        ]
    }

    try:
        json_data = json.dumps(slack_attachment)
        logger.info('\nOutput ' + str(json_data))
        if (color == "danger" or state_to_notify == "all"):
            slack_request = urllib.request.Request(slack_webhook_url, data=json_data.encode('ascii'),
                                                headers={'Content-Type': 'application/json'})
            slack_response = urllib.request.urlopen(slack_request)
    except Exception as em:
        logger.exception("EXCEPTION: " + str(em))
