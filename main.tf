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
  tags             = var.tags
  environment {
    variables = {
      slackwebhook = var.slackwebhook
      statestonotify = var.statestonotify
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
  name = "stepfunction-${data.aws_caller_identity.current.account_id}-deploy-notifications-rule"
  event_pattern =<<EOF
    {
  "source": [
    "aws.states"
  ],
  "detail-type": [
    "Step Functions Execution Status Change"
  ],
  "resources": [
    "aws_lambda_function.stepfunction_status_slack.arn"
  ]
}
EOF
}

resource "aws_cloudwatch_event_target" "lambda_stepfunctions_notifications" {
  arn = aws_lambda_function.stepfunction_status_slack.arn
  rule = aws_cloudwatch_event_rule.deploy_events_rule.name

  input_path = "$.detail"
}

resource "aws_lambda_permission" "allow_cloudwatch_stepfunction_notifications" {
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.stepfunction_status_slack.function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.deploy_events_rule.arn
}