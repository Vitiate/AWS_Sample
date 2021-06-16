import json
import boto3
import logging
import os
import requests

logger = logging.getLogger()
logger.setLevel(logging.INFO)

logger.info("Starting Execution")

slack_webhook_url = os.environ['slack_webhook_url']
if slack_webhook_url != "no_value":
    notify_slack = True
else:
    notify_slack = False

sns_topic = os.environ['sns_topic']
if sns_topic != "no_value":
    notify_sns = True
else:
    notify_sns = False


def slack_notification(pretext, message, webhook_url):
    slack_data = {'pretext': pretext, 'text': message}
    logger.info(f"Sending notification via {webhook_url}")
    response = requests.post(
        webhook_url, data=json.dumps(slack_data), headers={'Content-Type': 'application/json'}
    )
    print(response)
    if response.status_code != 200:
        raise ValueError(
            'Request to slack returned an error %s, the response is:\n%s'
            % (response.status_code, response.text)
        )
    return response


def notification_handler(message):
    # Sends notifications
    detail = {'Subject': "CloudFormation Drift Detection", 'Message': message}
    if notify_slack:
        slack_notification(pretext=detail['Subject'], message=detail['Message'],
                           webhook_url=slack_webhook_url)
    if notify_sns:
        response = boto3.client('sns').publish(TopicArn=sns_topic,
                                               Message=json.dumps(detail))


def lambda_handler(event, context):
    try:
        ACCOUNT_ID = context.invoked_function_arn.split(":")[4]
        REGION = context.invoked_function_arn.split(":")[3]
    except:
        # If the above fails then the function is being executed locally
        ACCOUNT_ID = 111111111
        REGION = "local-execution"
    status_code = 200
    stack_count = 0
    sync_count = 0
    drift_count = 0
    cfn_client = boto3.client("cloudformation")

    try:  # Try and get a list of stabalized cfn templates to test for drift
        logger.debug(
            "Obtain list of cloudformation stacks in the CREATE_COMPLETE or UPDATE_COMPLETE state")
        response = cfn_client.list_stacks(
            StackStatusFilter=[
                'CREATE_COMPLETE', 'UPDATE_COMPLETE'
            ]
        )
    except Exception as e:
        logger.error(f"list_stacks: Error {e}")
        status_code = 500

    logger.debug("Checking stacks for Drift Detection NOT_CHECKED")
    for stack in response['StackSummaries']:
        stack_count += 1
        if stack['DriftInformation']['StackDriftStatus'] == 'NOT_CHECKED':
            try:  # Enable drift detection
                logger.debug(f"Enable Drift Detection on {stack['StackName']}")
                response = cfn_client.detect_stack_drift(
                    StackName=stack['StackName'])
            except Exception as e:
                logger.error(f"detect_stack_drift: Error {e}")
                status_code = 500
        if stack['DriftInformation']['StackDriftStatus'] == 'DRIFTED':
            drift_count += 1
            notification_handler(
                f"{stack['StackName']} in {ACCOUNT_ID} Region {REGION} has been found in a DRIFTED state")
            logger.debug(f"{stack['StackName']} is found in a DRIFTED state")

    sync_count = stack_count - drift_count
    message = {
        "Status": {
            "StackCount": stack_count,
            "DriftCount": drift_count,
            "SyncCount": sync_count
        }
    }
    logger.info(json.dumps(message))

    return {
        'statusCode': status_code,
        'body': json.dumps(message)
    }
