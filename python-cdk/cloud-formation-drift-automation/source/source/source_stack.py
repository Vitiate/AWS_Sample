from aws_cdk import core as cdk

# For consistency with other languages, `cdk` is the preferred import name for
# the CDK's core module.  The following line also imports it as `core` for use
# with examples from the CDK Developer's Guide, which are in the process of
# being updated to use `cdk`.  You may delete this import if you don't need it.
from aws_cdk import core
from aws_cdk import(
    aws_iam,
    aws_events,
    aws_events_targets,
    aws_lambda as lambda_
)


######################################################################
# create deployment stack
######################################################################


class SourceStack(cdk.Stack):

    def __init__(self, scope: cdk.Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        naming_prefix = self.node.try_get_context("naming_prefix")

        ######################################################################
        # create IAM role for drift detection
        ######################################################################

        detection_inline_policies = {
            'allowCfnAccess': aws_iam.PolicyDocument(
                statements=[
                    aws_iam.PolicyStatement(
                        effect=aws_iam.Effect.ALLOW,
                        actions=[
                            'cloudformation:ListStacks',
                            'cloudformation:DetectStackDrift',
                            'cloudformation:DescribeStackResourceDrifts'
                        ],
                        resources=[
                            'arn:aws:cloudformation:*'
                        ]
                    )
                ]
            )
        }

        detection_role = aws_iam.Role(
            self,
            f"{naming_prefix}event-role",
            assumed_by=aws_iam.ServicePrincipal("lambda.amazonaws.com"),
            description=f"Role used ",
            path='/service-role/',
            managed_policies=[
                aws_iam.ManagedPolicy.from_aws_managed_policy_name(
                    'IAMReadOnlyAccess'),
                aws_iam.ManagedPolicy.from_aws_managed_policy_name(
                    'service-role/AWSLambdaBasicExecutionRole')
            ],  # Read Only Access needed for Drift Detection, and basic lambda permissions
            inline_policies=detection_inline_policies
        )

        ######################################################################
        # create lambda_drift_detection lambda class
        ######################################################################

        class lambda_drift_detection(core.Construct):
            def __init__(self, scope: core.Construct, id: str):
                super().__init__(scope, id)

                env_slack_webhook_url = self.node.try_get_context(
                    "env_slack_webhook_url")
                env_sns_topic = self.node.try_get_context(
                    "env_sns_topic")
                cron_schedule = self.node.try_get_context(
                    "cron_schedule")

                handler = lambda_.Function(self, "Drift_Detection",
                                           runtime=lambda_.Runtime.PYTHON_3_8,
                                           memory_size=160,
                                           timeout=core.Duration.seconds(30),
                                           code=lambda_.Code.from_asset(
                                               "resources"),
                                           handler="lambda_cfn_drift.lambda_handler",
                                           role=detection_role,
                                           environment=dict(
                                               slack_webhook_url=env_slack_webhook_url,
                                               sns_topic=env_sns_topic)
                                           )
                rule = aws_events.Rule(
                    self, "Rule",
                    schedule=aws_events.Schedule.expression(cron_schedule)
                )
                rule.add_target(aws_events_targets.LambdaFunction(handler))

        ######################################################################
        # create Lambda function for drift detection and notification
        ######################################################################

        lambda_drift_detection(self, "DriftDetection")
