import json
import os
import urllib.parse
import boto3
import io
import gzip
import re
import requests
import logging

logger = logging.getLogger()
logger.setLevel(logging.ERROR)

logger.info("Starting Execution")

USER_AGENTS = {"console.amazonaws.com", "Coral/Jakarta", "Coral/Netty4"}
IGNORED_EVENTS = {"DownloadDBLogFilePortion", "TestScheduleExpression", "TestEventPattern", "LookupEvents",
                  "listDnssec", "Decrypt", "REST.GET.OBJECT_LOCK_CONFIGURATION", "ConsoleLogin"}


slack_webhook_url = os.environ['slack_webhook_url']
if slack_webhook_url != "no_value":
    notify_slack = True
    logger.info(f"Found Slack Webhook {slack_webhook_url}")
else:
    notify_slack = False

sns_topic = os.environ['sns_topic']
if sns_topic != "no_value":
    notify_sns = True
    logger.info(f"Found SNS Topic {sns_topic}")
else:
    notify_sns = False


def slack_notification(pretext, message, webhook_url):
    slack_blocks = []
    slack_blocks.append({"type": "section", "text": {
                        "type": "mrkdwn", "text": pretext}})
    slack_blocks.append({"type": "divider"})
    slack_blocks.append({"type": "section", "text": {
                        "type": "mrkdwn", "text": message}})
    slack_data = json.dumps({'blocks': slack_blocks})

    logger.info(f"Sending notification via {webhook_url}")
    response = requests.post(
        webhook_url, data=slack_data, headers={
            'Content-Type': 'application/json'}
    )
    if response.status_code != 200:
        raise ValueError(
            'Request to slack returned an error %s, the response is:\n%s'
            % (response.status_code, response.text)
        )
    return response


def notification_handler(subject, message):
    # Sends notifications
    detail = {'Subject': subject, 'Message': message}
    if notify_slack:
        slack_notification(pretext=detail['Subject'], message=detail['Message'],
                           webhook_url=slack_webhook_url)
    if notify_sns:
        response = boto3.client('sns').publish(TopicArn=sns_topic,
                                               Message=json.dumps(detail))


def check_regex(expr, txt) -> bool:
    match = re.search(expr, txt)
    return match is not None


def match_user_agent(txt) -> bool:
    if txt in USER_AGENTS:
        return True

    expressions = (
        "signin.amazonaws.com(.*)",
        "^S3Console",
        "^\[S3Console",
        "^Mozilla/",
        "^console(.*)amazonaws.com(.*)",
        "^aws-internal(.*)AWSLambdaConsole(.*)",
    )

    for expresion in expressions:
        if check_regex(expresion, txt):
            return True

    return False


def match_readonly_event_name(txt) -> bool:
    # starts with
    expressions = (
        "^Get",
        "^Describe",
        "^List",
        "^Head",
    )
    for expression in expressions:
        if check_regex(expression, txt):
            return True

    return False


def match_ignored_events(event_name) -> bool:
    return event_name in IGNORED_EVENTS


def filter_user_events(event) -> bool:
    is_match = match_user_agent(event['userAgent'])
    is_read_only = match_readonly_event_name(event['eventName'])
    is_ignored_event = match_ignored_events(event['eventName'])
    is_in_event = 'invokedBy' in event['userIdentity'] and event['userIdentity']['invokedBy'] == 'AWS Internal'

    status = is_match and not is_read_only and not is_ignored_event and not is_in_event

    if status:
        logger.info('found event')
    else:
        logger.info('filtered out')

    return status


def get_user_email(principal_id) -> str:
    words = principal_id.split(':')
    if len(words) > 1:
        return words[1]
    return principal_id


def lambda_handler(event, context) -> None:
    """
    This functions processes CloudTrail logs from S3, filters events from the AWS Console, and publishes to SNS
    :param event: List of S3 Events
    :param context: AWS Lambda Context Object
    :return: None
    """
    s3 = boto3.client('s3')
    for record in event['Records']:
        # Get the object from the event and show its content type
        bucket = record['s3']['bucket']['name']
        key = urllib.parse.unquote_plus(
            record['s3']['object']['key'], encoding='utf-8')
        try:
            logger.info(f"Bucket: {bucket}")
            logger.info(f"Key: {key}")
            response = s3.get_object(Bucket=bucket, Key=key)
            content = response['Body'].read()
            with gzip.GzipFile(fileobj=io.BytesIO(content), mode='rb') as fh:
                event_json = json.load(fh)
                output_dict = [
                    record for record in event_json['Records'] if filter_user_events(record)
                ]
                if len(output_dict) > 0:

                    message = ""
                    for item in output_dict:
                        account_id = item['recipientAccountId']
                        user_email = get_user_email(
                            item['userIdentity']['principalId'])
                        item_name = get_request(item['requestParameters'])
                        message = message + \
                            f"User `{user_email}` Performed `{item['eventName']}` On `{item_name}`\n"
                    subject = f"Manual Console Change Detected on {account_id}"
                    notification_handler(subject, message)
                    logger.info(message)
            return response['ContentType']
        except Exception as e:
            if 'NoneType' in str(e):
                logger.info(e)
                message = f"""
                  NoneType parsing error actual exception: {e}
              """
                logger.info(message)
            else:
                logger.error(e)
                message = f"""
                  Error getting object {key} from bucket {bucket}.
                  Make sure they exist and your bucket is in the same region as this function.
                  Actual exception: {e}
              """
                logger.info(message)
                raise e


def get_request(request):
    for item in request:
        if 'name' in item.lower():
            return request[item]
        elif 'groupid' in item.lower():
            return request[item]
        else:
            return f"Unknown Item Data:{item} add to lambda"


def unit_test() -> None:
    with open('sample.txt') as json_file:
        event_json = json.load(json_file)
        output_dict = [record for record in event_json['Records']
                       if filter_user_events(record)]
        for item in output_dict:
            user_email = get_user_email(item['userIdentity']['principalId'])
            print(f"{user_email} -- {item['eventName']}")
            user_email = get_user_email(item['userIdentity']['principalId'])
            message = f"{message} Manual Change {user_email} {item['eventName']}"
