import os, json, boto3, logging, requests

logger = logging.getLogger()
logger.setLevel(logging.WARNING)
# Look for the following tag to bypass the remediation
tag_to_test_for = os.environ['tag_to_test_for']

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


def validate_bucket(event, ACCOUNT_ID, REGION):
    #   Tests and remediates a s3 bucket
    message = ""
    event = json.loads(event)
    logger.info(event)
    bucket = event['detail']['requestParameters']['bucketName']
    public_access_block = True
    try:
        response = boto3.client('s3').get_bucket_tagging(Bucket=bucket)
        bucket_tags = response['TagSet']
        logger.info(f"Received Tags: {bucket_tags}")
    except Exception as e:
        if '(NoSuchTagSet)' in str(e):
            logger.info("No tags attached to the bucket")
            bucket_tags = [{'Key': 'none', 'Value': 'none'}]
        elif '(NoSuchBucket)' in str(e):
            logger.info(f"Bucket {bucket} does not exist")
            return {
                'statusCode': 200,
                'body': json.dumps(f"Bucket {bucket} does not exist")
            }
        else:
            logger.error(e)
            raise Exception(e)

    if not test_tag(bucket_tags):
        logger.info("No exclusion tag found, processing bucket")
        try:
            response = boto3.client('s3').get_public_access_block(Bucket=bucket)
        except Exception as e:
            if "The public access block configuration was not found" in str(e):
                public_access_block = False
                message = f"\n      Bucket {bucket} created with no public access block by {event['detail']['userIdentity']['arn']}"
            else:
                logger.error(e)
                raise Exception(e)
        if public_access_block:
            logger.info("Found access block config on bucket, verifying configuration")
            for i in response['PublicAccessBlockConfiguration']:
                logger.info(f"Checking: {i} {response['PublicAccessBlockConfiguration'][i]}")
                if not response['PublicAccessBlockConfiguration'][i]:
                    message = message + f"\n        Invalid {i} ACL"
                    public_access_block = False
                continue
        if not public_access_block:
            try:
                detail = {}
                logger.info(f"Attempt to apply default access block to {bucket}")
                #response = boto3.client('s3').put_public_access_block(Bucket=bucket,
                #                                                      PublicAccessBlockConfiguration=default_public_access_block)
                message = message + f"\n    Remediation of s3 Bucket: {bucket} on {ACCOUNT_ID} in {REGION} completed"
                return message
            except Exception as e:
                print(e)
                raise e


def notification_handler(message):
    # Sends notifications
    message = message + f"\n If this was modified in error please apply the {tag_to_test_for} tag to the s3 bucket"
    detail = {'Subject': "s3 Bucket Auto Remediation", 'Message': message}
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
        # If the above fails then the function is being executed in a local debugger.
        ACCOUNT_ID = 111111111
        REGION = "local-execution"

    message = ""
    response = ""
    default_public_access_block = {
        'BlockPublicAcls': True,
        'IgnorePublicAcls': True,
        'BlockPublicPolicy': True,
        'RestrictPublicBuckets': True
    }

    if 'Scheduled Event' in event['detail-type']:
        # This is a scheduled event, get all the buckets on the account and validate them.
        s3 = boto3.client('s3')
        try:
            response = s3.list_buckets()

        except Exception as e:
            logger.error(e)
            raise Exception(e)
        for bucket in response['Buckets']:
            logger.info(f"Processing Bucket {bucket['Name']}")
            forged_event = {
                "detail": {
                    "requestParameters": {
                        "bucketName": bucket['Name']
                    },
                    "userIdentity": {
                        "arn": "Automated Bucket Audit"
                    }
                }
            }
            message_line = validate_bucket(json.dumps(forged_event), ACCOUNT_ID, REGION)
            if message_line:
                message = str(message) + str(message_line) + "\n"

        notification_handler(message)
        return {
            'statusCode': 200,
            'body': json.dumps("Scheduled bucket validation completed")
        }

    if 'detail' not in event or ('detail' in event and 'eventName' not in event['detail']):
        return {"Result": "Failure", "Message": "Lambda not triggered by an event"}

    if event['detail']['eventName'] == 'CreateBucket':
        message = validate_bucket(event, ACCOUNT_ID, REGION)
        notification_handler(message)
    return {
        'statusCode': 200,
        'body': json.dumps("exit")
    }


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


def test_tag(tags):
    logger.info("Testing for exclusion tag")
    try:
        for i in tags:
            if tag_to_test_for in i['Key']:
                logger.info("Found exclusion tag")
                return True
    except Exception as e:
        logger.error(str(e))
        pass
    return False
