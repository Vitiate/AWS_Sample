import boto3
import botocore
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
#
#   Creates the objects required to setup the forwarding of s3 bucket put notifications from
#   cloudtrail to another account so that a lambda function in the other account can retrieve
#   files / logs from the s3 bucket.
#


def validate_cdk_json(context):
    print('\ncdk.json validation\n')
    naming_prefix = context.node.try_get_context("naming_prefix")
    print(f"Naming Prefix is: {naming_prefix}, all objects created will be prefixed with this name\n ie: {naming_prefix}-aes-siem-cloudtrail-event-12345678-us-east-1")


__version__ = '1.0.0-beta.1'
print(__version__)


class EventBridgeShipperStack(core.Stack):

    def __init__(self, scope: core.Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        validate_cdk_json(self)
        naming_prefix = self.node.try_get_context("naming_prefix")

        s3bucket_name = f'{naming_prefix}aes-siem-cloudtrail-eventlog{core.Aws.ACCOUNT_ID}-{core.Aws.REGION}'
        s3bucket_expiration = self.node.try_get_context("s3_retention_days")
        event_bus_arn = self.node.try_get_context("event_bus_arn")
        bucket_monitor_prefix = self.node.try_get_context(
            "bucket_monitor_prefix")

        ######################################################################
        # create kms key
        ######################################################################
        kms_key = aws_kms.Key(
            self, f'{naming_prefix}aes-event-bucket-key', description='CMK for Cloudtrail Event Bucket',
            removal_policy=core.RemovalPolicy.RETAIN)

        kms_key.add_alias(
            alias_name=f'{naming_prefix}aes-event-bucket-alias'
        )

        kms_key.add_to_resource_policy(
            aws_iam.PolicyStatement(
                sid='Allow CloudTrail to use this key',
                actions=['kms:Encrypt', 'kms:Decrypt', 'kms:ReEncrypt*',
                         'kms:GenerateDataKey*', 'kms:DescribeKey'],
                principals=[aws_iam.ServicePrincipal(
                    'cloudtrail.amazonaws.com')],
                resources=['*'],),)

        ######################################################################
        # create s3 bucket
        ######################################################################
        block_pub = aws_s3.BlockPublicAccess(
            block_public_acls=True,
            ignore_public_acls=True,
            block_public_policy=True,
            restrict_public_buckets=True
        )
        s3_bucket = aws_s3.Bucket(
            self, 'S3BucketForCloudTrailEvents', block_public_access=block_pub,
            bucket_name=s3bucket_name,
            removal_policy=core.RemovalPolicy.DESTROY
        )
        s3_bucket.add_lifecycle_rule(
            expiration=core.Duration.days(int(s3bucket_expiration))
        )

        ######################################################################
        # create cloudtrail
        ######################################################################
        cloudtrail = aws_cloudtrail.Trail(
            self,
            id=f"{naming_prefix}Trail",
            bucket=s3_bucket,
            is_multi_region_trail=False
        )

        cloudtrail.add_event_selector(
            data_resource_type=aws_cloudtrail.DataResourceType("S3_OBJECT"),
            data_resource_values=["arn:aws:s3"]
        )

        ######################################################################
        # create IAM role for event rule
        ######################################################################

        event_iam_policy_statement = aws_iam.PolicyStatement(
            actions=["events:PutEvents"],
            resources=[f"{event_bus_arn}"]
        )
        event_iam_policy_document = aws_iam.PolicyDocument(
            assign_sids=True,
            statements=[event_iam_policy_statement]
        )

        event_iam_policy = aws_iam.Policy(
            self,
            "aes-iam-policy",
            document=event_iam_policy_document
        )

        #events_principle = aws_iam.Iprincipal.grant_principal("events.amazonaws.com")

        event_iam_role = aws_iam.Role(
            self,
            f"{naming_prefix}event-role",
            assumed_by=aws_iam.ServicePrincipal("events.amazonaws.com"),
            description=f"Role used by the aes-siem event rule to forward events to {event_bus_arn}",
        )

        event_iam_role.attach_inline_policy(
            policy=event_iam_policy
        )

        ######################################################################
        # create Event Rule
        ######################################################################

        event_rule = aws_events.Rule(
            self,
            f"{naming_prefix}aes-event-rule",
            description="Event bridge rule to forward s3 put notifications to the log account",
            enabled=True
        )

        event_rule.add_event_pattern(
            detail={
                "eventSource": ["s3.amazonaws.com"],
                "eventName": ["putObject"],
                "requestParameters": {
                    "bucketName": [f"{bucket_monitor_prefix}"]
                }
            }
        )

        # Point the rule at the remote event bus

        rule_target = aws_events.RuleTargetConfig(
            arn=event_bus_arn,
            role=event_iam_role,
            id=f"{naming_prefix}-aes-bus"
        )

#        remote_event_bus = aws_events.EventBus(self, f"{naming_prefix}-bust-target").from_event_bus_arn(
#            scope=self, id=f"{naming_prefix}-aes-bus", event_bus_arn=event_bus_arn)
        event_rule.add_target(
            target=aws_events.IRuleTarget.bind(self, rule=rule_target))
