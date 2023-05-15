data "aws_caller_identity" "current" {}
data "aws_region" "current" {}

locals {
  current_account_id = data.aws_caller_identity.current.account_id
  current_region     = data.aws_region.current.name
}

data "archive_file" "lambda_stepfunction_status_slack_src" {
  type        = "zip"
  source_file = "${path.module}/src/pipeline-status-slack.py"
  output_path = "${path.module}/src/pipeline-status-slack.zip"
}

resource "aws_lambda_function" "stepfunction_status_slack" {
  function_name    = "${var.name_prefix}-infra-pipeline-status-slack"
  handler          = "pipeline-status-slack.lambda_handler"
  role             = aws_iam_role.lambda_stepfunction_status_slack_exec.arn
  runtime          = "python3.7"
  filename         = data.archive_file.lambda_stepfunction_status_slack_src.output_path
  source_code_hash = filebase64sha256(data.archive_file.lambda_stepfunction_status_slack_src.output_path)
  timeout          = var.lambda_timeout
  tags             = var.tags
  environment {
    variables = {
      REPORT_FAILED_EVENTS_ON_SUCCESS = var.report_failed_events_on_success
      slackwebhook                    = var.slackwebhook
      statestonotify                  = var.statestonotify
      TAG_CHANNEL_ON_FAILURE          = var.tag_channel_on_failure
    }
  }
}

resource "aws_iam_role" "lambda_stepfunction_status_slack_exec" {
  name               = "${var.name_prefix}-infra-pipeline-status-slack"
  assume_role_policy = data.aws_iam_policy_document.lambda_assume.json
  tags               = var.tags
}

resource "aws_iam_role_policy" "logs_to_stepfunction_status_slack_lambda" {
  policy = data.aws_iam_policy_document.logs_for_lambda.json
  role   = aws_iam_role.lambda_stepfunction_status_slack_exec.id
}

resource "aws_cloudwatch_event_rule" "deploy_events_rule" {
  name        = "${var.name_prefix}-sfn-execution-change"
  description = "Triggers when an AWS Step Functions state machine execution starts, succeeds or fails"
  tags        = var.tags
  event_pattern = <<EOF
{
  "source": [
    "aws.states"
  ],
  "detail-type": [
    "Step Functions Execution Status Change"
  ],
  "detail": {
    "stateMachineArn": ${
  length(var.state_machine_arns) > 0
  ? jsonencode(var.state_machine_arns)
  # This pattern will match all state machine ARNs
: jsonencode([{ prefix = "" }])}
  }
}
EOF
}

resource "aws_cloudwatch_event_target" "lambda_stepfunctions_notifications" {
  arn  = aws_lambda_function.stepfunction_status_slack.arn
  rule = aws_cloudwatch_event_rule.deploy_events_rule.name
}

resource "aws_lambda_permission" "allow_cloudwatch_stepfunction_notifications" {
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.stepfunction_status_slack.function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.deploy_events_rule.arn
}
