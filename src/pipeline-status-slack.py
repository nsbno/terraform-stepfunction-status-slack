import os
import logging
import json
import urllib
import boto3
from datetime import datetime
from urllib import request

logger = logging.getLogger()
logger.setLevel(logging.INFO)


def find_event_by_backtracking(initial_event, events, condition_fn, break_fn=None):
    """Backtracks to the first event that matches a specific condition and returns that event"""
    event = initial_event
    visited_events = []
    for _ in range(len(events)):
        if condition_fn(event):
            return event
        if break_fn and break_fn(visited_events):
            event = None
            break
        visited_events.append(event)
        event = next(
            (e for e in events if e["id"] == event["previousEventId"]), None
        )
        if event is None:
            break
    return event


def get_fail_events(events, excluded_states=[]):
    """Return the events that failed during an execution"""
    fail_events = []
    for e in events:
        # Different state types use different names for storing details about the failed event
        # `taskFailedEventDetails`, `activityFailedEventDetails`, etc.
        failed_event_details = e.get(next((key for key in e if (key.endswith(
            "FailedEventDetails") or key.endswith("TimedOutEventDetails")) and all(required_key in e[key] for required_key in ["error"])), None), None)
        if failed_event_details and (e["type"].endswith("Failed") or e["type"].endswith("TimedOut")) and e["type"] != "ExecutionFailed":
            enter_event = find_event_by_backtracking(e, events, lambda current_event: current_event["type"].endswith("StateEntered") and current_event["stateEnteredEventDetails"]["name"] not in excluded_states, break_fn=lambda visited_events: any(
                visited_event["type"].endswith("StateEntered") for visited_event in visited_events))
            if enter_event:
                state_name = enter_event["stateEnteredEventDetails"]["name"]
                # Save failed_event_details to `failedEventDetails` to make it easier and more consistent to reference
                fail_events.append(
                    {**e, "name": state_name, "failedEventDetails": failed_event_details})
    return fail_events


def get_failed_message(execution_arn, client=None):
    """Returns a Markdown-formatted string describing what made the execution fail"""
    if client is None:
        client = boto3.client("stepfunctions")
    response = client.get_execution_history(
        executionArn=execution_arn, maxResults=500, reverseOrder=True
    )
    events = response["events"]
    fail_events = get_fail_events(events, excluded_states=["Raise Errors"])
    logger.info("Found %s failed states", len(fail_events))

    if len(fail_events):
        if len(fail_events) == 1:
            return (
                f"*Status:* Failed in state `{fail_events[0]['name']}`\n"
                f"*Error:* `{fail_events[0]['failedEventDetails']['error']}`\n"
                f"{'```' + fail_events[0]['failedEventDetails']['cause'] + '```' if 'cause' in fail_events[0]['failedEventDetails'] else ''}"
            )
        else:
            state_names = ', '.join([f"`{e['name']}`" for e in fail_events])
            errors = "\n".join(
                [(
                    f"`{e['name']}` failed due to `{e['failedEventDetails']['error']}`:\n"
                    f"{'```' + e['failedEventDetails']['cause'] + '```' if 'cause' in e['failedEventDetails'] else ''}"
                ) for e in fail_events])
            return (
                f"*Status:* Failed in states {state_names}\n"
                f"*Errors:*\n"
                f"{errors}"
            )
    return (
        f"*Status:* Failed in state `Unknown state`\n"
        f"*Error:* `Unknown error`\n"
        f"```Unknown```"
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
    execution_input = json.loads(event["detail"]["input"])
    toggling_cost_saving_mode = execution_input.get(
        "toggling_cost_saving_mode", False)
    slack_message = [
        f"*Execution:* <{execution_url}|{execution_name}>"
    ]
    footer = ""
    if all(key in execution_input for key in ["git_user", "git_repo", "git_branch"]):
        footer = f"{execution_input['git_user']} @ {execution_input['git_repo']} ({execution_input['git_branch']})"

    if toggling_cost_saving_mode:
        slack_message.append(
            f"*Type:* Automatic deployment (toggling cost-saving mode)")

    if status == 'RUNNING':
        slack_color = 'good'
        slack_message.append("*Status:* Started")
        slack_message.append(f"*Execution Input*:\n```{json.dumps(execution_input, sort_keys=True, indent=2)}```")
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
    else:
        slack_color = 'danger'
        slack_message.append(f'*Status:* Unknown execution status `{status}`')

    slack_attachment = {
        "attachments": [
            {
                "title": state_machine_name,
                "fallback": "fallback",
                "text": "\n".join(slack_message),
                "color": slack_color,
                "mrkdwn_in": ["text"],
                "footer": footer,
                "ts": int(timestamp.timestamp())
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
