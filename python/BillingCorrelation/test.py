import re
from socket import EWOULDBLOCK
import boto3
import os
import json
import logging

logger = logging.getLogger()
logger.setLevel(logging.INFO)

logger.info("Starting Execution")


cfn_client = boto3.client('cloudformation')
ce_client = boto3.client('ce')
org_client = boto3.client('organizations')
# Hourly Exmaple, must be the last 14 days
#Start = '2021-07-01T00:00:00Z'
#End = '2021-07-30T23:59:59Z'
#Granularity = 'HOURLY'
# Daily Exmaple, must be the last 14 days
Start = '2021-06-08'
End = '2021-07-30'
Granularity = 'DAILY'
Metrics = ['UnblendedCost']
GroupBy = [{'Type': 'DIMENSION', 'Key': 'SERVICE'}]

#response = org_client.list_accounts()

# try:  # Try and get a list of aws accounts from the master account
#    logger.debug(
#        "Obtain list of AWS accounts from the master account")
#    NextToken = " "
#    StackList = []
#
#    response = org_client.list_accounts()
#    results = response['Accounts']
#    while "NextToken" in response:
#        response = org_client.list_accounts(
#            NextToken=response["NextToken"]
#        )
#        results.extend(response)['Accounts']
# except Exception as e:
#    logger.error(f"list_accounts: Error {e}")
#    status_code = 500

# for account in results:
logger.debug(f"Get all CFN changes")
try:
    NextToken = " "
    response = cfn_client.describe_stacks()
    cfn_results = response['Stacks']
    while "NextToken" in response:
        response = cfn_client.describe_stacks(
            NextToken=response['NextToken']
        )
        cfn_results.extend(response['Stacks'])
except Exception as e:
    print(f'An error occured making the request {e}')

print("StackName,StackId,LastUpdate")
for stack in cfn_results:
    last_update = stack['CreationTime']
    if 'LastUpdatedTime' in response:
        last_update = stack['LastUpdatedTime']

    print(f'{stack["StackName"]},{stack["StackId"]},{last_update}')

#try:
#    NextToken = " "
#    response = ce_client.get_cost_and_usage(
#        TimePeriod={'Start': Start, 'End': End}, Granularity=Granularity, Metrics=Metrics, GroupBy=GroupBy)
#    billing_results = response['ResultsByTime']
#    while "NextToken" in response:
#        response = ce_client.get_cost_and_usage(
#            TimePeriod={'Start': Start, 'End': End}, Granularity=Granularity, Metrics=Metrics, NextToken=response['NextToken'], GroupBy=GroupBy)
#        billing_results.extend(response['ResultsByTime'])
#except Exception as e:
#    print(f'An error occured making the request {e}')
#
#print("Start, End, Service,Amount,Unit")
#for billing_result in billing_results:
#    for group in billing_result['Groups']:
#        for key in group['Keys']:
#            print(
#                f"{billing_result['TimePeriod']['Start']},{billing_result['TimePeriod']['End']},{key},{group['Metrics']['UnblendedCost']['Amount']},{group['Metrics']['UnblendedCost']['Unit']}")
