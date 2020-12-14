## terraform-aws-pipeline-slack-notifier
_A companion module for the Continuous Deployment pipeline in https://github.com/nsbno/aws-sfn-deployment-pipeline/_

A Terraform module that sends messages to Slack when an AWS Step Functions state machine starts, ends or fails. For a failed execution, the module will fetch the execution details and add any error messages to the the Slack message. The module can be configured to send messages for all kinds of updates (default), or only on errors.

## Example message
![Slack Message](https://user-images.githubusercontent.com/10640491/98384643-545f4600-204e-11eb-9a68-fafd09b2f35e.png)
