data "aws_caller_identity" "current-account" {}
data "aws_region" "current" {}

locals {
  current_account_id = data.aws_caller_identity.current-account.account_id
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
