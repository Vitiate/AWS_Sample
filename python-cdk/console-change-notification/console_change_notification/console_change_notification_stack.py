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


class ConsoleChangeNotificationStack(cdk.Stack):

    def __init__(self, scope: cdk.Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        naming_prefix = self.node.try_get_context("naming_prefix")
        cloud_trail_bucket = self.node.try_get_context("cloud_trail_bucket")
        ######################################################################
        # create IAM role for manual mod detection stack
        #####################################################################

        detection_inline_policies = {
            'allowCfnAccess': aws_iam.PolicyDocument(
                statements=[
                    aws_iam.PolicyStatement(
                        effect=aws_iam.Effect.ALLOW,
                        actions=[
                            's3:GetObject'
                        ],
                        resources=[
                            f'arn:aws:s3:::{cloud_trail_bucket}',
                            f'arn:aws:s3:::{cloud_trail_bucket}/*'
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

        class lambda_modification_detection(core.Construct):
            def __init__(self, scope: core.Construct, id: str):

                super().__init__(scope, id)

                env_slack_webhook_url = self.node.try_get_context(
                    "env_slack_webhook_url")
                env_sns_topic = self.node.try_get_context(
                    "env_sns_topic")

                handler = lambda_.Function(self, "Modification_Detection",
                                           runtime=lambda_.Runtime.PYTHON_3_8,
                                           memory_size=160,
                                           timeout=core.Duration.seconds(30),
                                           code=lambda_.Code.from_asset(
                                               "resources"),
                                           handler="lambda_console_notify.lambda_handler",
                                           role=detection_role,
                                           environment=dict(
                                               slack_webhook_url=env_slack_webhook_url,
                                               sns_topic=env_sns_topic)
                                           )
                self.arn = handler.function_arn
        ######################################################################
        # create Lambda function for manual mod detection and notification
        ######################################################################
        lambda_function = lambda_modification_detection(
            self, "ModificationDetection")

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
            arn=lambda_function.arn,
            id=f"{naming_prefix}manual-mod-trigger",
            input_transformer=input_transformer_property
        )
        # Put target property into a list
        target_list = []
        target_list.append(lambda_target)
        # Create the rule
        event_rule = aws_events.CfnRule(
            self,
            id=f"{naming_prefix}manual-mod-rule",
            event_pattern={
                "source": ["aws.s3"],
                "detail-type": ["AWS API Call via CloudTrail"],
                "detail": {
                    "eventSource": ["s3.amazonaws.com"],
                    "eventName": ["PutObject"],
                    "requestParameters": {
                        "bucketName": [f"{cloud_trail_bucket}"]
                    }
                }
            },
            targets=target_list
        )
