from logging import error
import boto3
import botocore
import typing
from botocore.exceptions import ClientError
from aws_cdk import (
    aws_cloudtrail,
    aws_events,
    aws_events_targets,
    aws_iam,
    aws_kms,
    aws_s3,
    core,
)


def validate_cdk_json(context):
    print('\ncdk.json validation\n')
    naming_prefix = context.node.try_get_context("naming_prefix")
    print(f"Naming Prefix is: {naming_prefix}, all objects created will be prefixed with this name\n ie: {naming_prefix}-aes-siem-cloudtrail-event-12345678-us-east-1")


__version__ = '1.0.0-beta.1'
print(__version__)


class EventBridgeRecieverStack(core.Stack):

    def __init__(self, scope: core.Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        validate_cdk_json(self)
        naming_prefix = self.node.try_get_context("naming_prefix")
        aws_organization = boto3.client('organizations')
        lambda_function_arn = self.node.try_get_context("lambda_function_arn")
        try:
            response = aws_organization.describe_organization()
            orgId = response['Organization']['Id']
            print(f"Obtained Org Id: {orgId}")
        except:
            print("Failed to obtain org id for organization")

        ######################################################################
        # create event bus
        ######################################################################
        event_bus = aws_events.EventBus(
            self,
            id=f"{naming_prefix}Event-Bus",
            event_bus_name=f"{naming_prefix}Event-Bus"
        )
        event_bus.apply_removal_policy(core.RemovalPolicy.DESTROY)

        bus_statement = {
            "Statement": [{
                "Sid": "Allow Org ID Access",
                "Effect": "Allow",
                "Principal": "*",
                "Action": "events:PutEvents",
                "Resource": event_bus.event_bus_arn,
                "Condition": {
                    "StringEquals": {
                        "aws:PrincipalOrgID": f"{orgId}"
                    }
                }
            }]
        }

        # Limit access to the event bus to put events from the organization
        event_bus_policy = aws_events.CfnEventBusPolicy(
            scope=self,
            id=f"{naming_prefix}Org-Access-Id",
            statement_id=f"{naming_prefix}Org-Access",
            action="events:PutEvents",
            condition={'type': 'StringEquals',
                       'key': 'aws:PrincipalOrgID', 'value': orgId},
            principal="*",
            event_bus_name=event_bus.event_bus_name
        )

        ######################################################################
        # create event rule
        ######################################################################

        # Setup Mapping for the input tranformer
        input_paths_map = {}
        input_paths_map['bucketName'] = '$.detail.requestParameters.bucketName'
        input_paths_map['key'] = '$.detail.requestParameters.key'
        # Define the input transformer
        input_transformer_property = aws_events.CfnRule.InputTransformerProperty(
            input_template='{\"Records\": [{\n \"s3\": {\n \"bucket\": {\n \"name\": \"<bucketName>\"\n },\n \"object\": {\n \"key\": \"<key>\"}}}]}',
            input_paths_map=input_paths_map
        )
        # Create Lambda target
        lambda_target = aws_events.CfnRule.TargetProperty(
            arn=lambda_function_arn,
            id=f"{naming_prefix}aes-loader-trigger",
            input_transformer=input_transformer_property
        )
        # Put target property into a list
        target_list = []
        target_list.append(lambda_target)
        # Create the rule
        cfn_rule = aws_events.CfnRule(
            self,
            id=f"{naming_prefix}aes-event-rule",
            event_bus_name=event_bus.event_bus_arn,
            event_pattern={
                "eventSource": ["s3.amazonaws.com"],
                "eventName": ["putObject"]
            },
            targets=target_list
        )
