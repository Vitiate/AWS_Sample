import json
import boto3
from datetime import datetime
from datetime import timedelta
from botocore.exceptions import ClientError

list_users_to_remove = []
list_access_keys_to_remove = []
date_now = datetime.now()
iam_client = boto3.client('iam')
max_idle_days = 90
max_items = 50

def lambda_handler(event, context):

    try:
        res_users = iam_client.list_users(
            MaxItems=max_items
        )
        check_credentials(res_users)
    except ClientError as error:
        print('An error occurred while fetching user list.', error)
        return

    if res_users['IsTruncated']:
        while res_users['IsTruncated']:
            marker = res_users['Marker']
            try:
                res_users = iam_client.list_users(
                    Marker=marker,
                    MaxItems=max_items
                )

                check_credentials(res_users)
            except ClientError as error:
                print('An error occurred while fetching user list.', error)
                return
    return {
        'statusCode': 200,
        'body': json.dumps('credential-enforcement processed successfully')
    }


def check_credentials(res_users):
    created_date = datetime.now()
    last_used_date = datetime.now()
    access_key_id = None

    for user in res_users['Users']:
        user_tags = iam_client.list_user_tags(UserName=user['UserName'])
        if 'au:credentialenforcement' in user_tags:                     # Check to see if an exemption tag exists on the user
            print('User ' + user['UserName'] + ' exempt from credential enforcement')
        else:                                                           # If the tag exists we ignore the user
            try:
                if 'PasswordLastUsed' in user:                              # Checking for console user password last usage
                    last_used_date = user['PasswordLastUsed'].replace(tzinfo=None)
                    difference = date_now - last_used_date
                    if difference.days > max_idle_days:                     # Last login is greater then idle days, remove console access
                        response = iam_client.delete_login_profile(UserName=user['UserName'])
            except ClientError as error:
                print('An error occurred while processing passwords', error)
                return
            try:
                res_keys = iam_client.list_access_keys(
                    UserName=user['UserName'],
                    MaxItems=2)
                if 'AccessKeyMetadata' in res_keys:                     # Found access keys, process them
                    for key in res_keys['AccessKeyMetadata']:
                        if 'CreateDate' in key:
                            created_date = res_keys['AccessKeyMetadata'][0]['CreateDate'].replace(tzinfo=None)
                        if 'AccessKeyId' in key:
                            access_key_id = key['AccessKeyId']
                            res_last_used_key = iam_client.get_access_key_last_used(
                                AccessKeyId=access_key_id)
                            if 'LastUsedDate' in key:
                                last_used_date = res_last_used_key['AccessKeyLastUsed']['LastUsedDate'].replace(tzinfo=None)
                            else:
                                last_used_date = created_date
                            difference = date_now - last_used_date
                            if difference.days > max_idle_days:         # If the access key is older then the idle time delete it
                                response = iam_client.delete_access_key(UserName=user['UserName'], AccessKeyId=access_key_id)

            except ClientError as error:
                print('An error occurred while processing access keys', error)
                return

