import os
import logging
import json
import urllib
import boto3
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
    message.append("Time: " + event['time'])
    message.append("Executionname: " + executionname)
    message.append("Status: No issues")

    if (color == "danger"):
        client = boto3.client("stepfunctions")
        output = client.get_execution_history(executionArn=executionarn)
        logger.info('\nFailed ' + str(output))

        try:
            for eventer in output["events"]:
                if ("ExecutionFailed" in eventer["type"]):
                    cause = str(eventer["executionFailedEventDetails"]["cause"])
                    aktivitity = cause.split("'")[1]
                    message[2]= ("Failed: " + aktivitity + "\n" + " Error: " + cause)
        except Exception:
            aktivitity = 'Unknown'
            cause = 'Unknown'
        
    slack_attachment = {
        "attachments": [
            {
                "title": pipelinename + "-" + event['detail']['status'],
                "fallback": "fallback",
                "text": message[0] + "\n" + message[1] + "\n" + message[2],
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
