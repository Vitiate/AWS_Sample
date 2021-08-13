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
    aws_lambda as lambda_,
    aws_cloudtrail,
    aws_s3,
    aws_kms,
    aws_logs
)
from aws_cdk.aws_ec2 import Action
import boto3


class ConsoleChangeNotificationStack(cdk.Stack):

    def __init__(self, scope: cdk.Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        def create_kms(self, key):
            ######################################################################
            # create kms key
            #####################################################################
            print("Creating KMS_Key")
            kmskey = aws_kms.Key(self,
                                 id=key['alias'],
                                 alias=key['alias'],
                                 description=key['description'],
                                 enabled=True,
                                 enable_key_rotation=key['enable-key-rotation']
                                 )
            for principle in key['service-principles']:
                print(f"Grant E/D to on {key['alias']} to {principle}")
                iam_principle = aws_iam.ServicePrincipal(service=principle)
                kmskey.grant_encrypt_decrypt(iam_principle)
            return({key['alias']: kmskey})

        def create_s3_bucket(self, cloud_trail_config, s3_bucket_key, service_principals):
            ######################################################################
            # create s3 bucket
            #####################################################################
            print("Create s3 Bucket")
            s3_bucketname = cloud_trail_config['cloud_trail_bucket']
            s3_hash = hash(s3_bucketname) % 10**8
            s3_bucketname = f"{s3_bucketname}-{s3_hash}"
            block_pub = aws_s3.BlockPublicAccess(
                block_public_acls=True,
                ignore_public_acls=True,
                block_public_policy=True,
                restrict_public_buckets=True
            )
            s3_bucket = aws_s3.Bucket(
                self, 'S3BucketForChangeNotfication', block_public_access=block_pub,
                bucket_name=s3_bucketname,
                removal_policy=core.RemovalPolicy.DESTROY,
                encryption_key=s3_bucket_key,
                encryption=aws_s3.BucketEncryption('KMS')
            )
            for service in service_principals:
                print(f"Adding principal: {service} to bucket")
                s3_bucket.add_to_resource_policy(permission=aws_iam.PolicyStatement(
                    actions=["s3:GetBucketAcl"],
                    effect=aws_iam.Effect.ALLOW,
                    principals=[aws_iam.ServicePrincipal(service)],
                    resources=[s3_bucket.bucket_arn]
                ))
                s3_bucket.add_to_resource_policy(permission=aws_iam.PolicyStatement(
                    actions=["s3:PutObject"],
                    effect=aws_iam.Effect.ALLOW,
                    principals=[aws_iam.ServicePrincipal(service)],
                    conditions={
                        "StringEquals": {
                            "s3:x-amz-acl": "bucket-owner-full-control"
                        }
                    },
                    resources=[
                        f"{s3_bucket.bucket_arn}/*",
                        s3_bucket.bucket_arn
                    ]
                ))

            return(s3_bucketname, s3_bucket)

        def create_log_group(self, cloud_trail_config, cloudwatch_key):
            ######################################################################
            # create cloudwatch log group
            #####################################################################
            print("Create Log Group for Cloudtrail")
            loggroup_name = cloud_trail_config['cloud_watch_log_group']
            s3_hash = hash(loggroup_name) % 10**8
            loggroup_name = f"{loggroup_name}-{s3_hash}"

            loggroup = aws_logs.LogGroup(
                self,
                id=loggroup_name,
                log_group_name=loggroup_name,
                encryption_key=cloudwatch_key)

            return(loggroup.log_group_arn)

        def create_cloudtrail(self, cloud_trail_config, cloud_trail_bucket, cloud_watch_loggroup, cloud_trail_kms, depends_on):
            ######################################################################
            # create cloudtrail
            #####################################################################
            print("Creating CloudTrail")
            iam_role_cloudwatch = aws_iam.Role(
                scope=self,
                id="CloudTrailToCloudWatch",
                assumed_by=aws_iam.ServicePrincipal(
                    'cloudtrail.amazonaws.com'),
                description='Allows Cloudtrail access to a loggroup',
                inline_policies=[aws_iam.PolicyDocument(statements=[####
                    aws_iam.PolicyStatement(
                        actions=["logs:CreateLogStream",
                                 "logs:PutLogEvents"],
                        effect=aws_iam.Effect.ALLOW,
                        
                        resources=[cloud_watch_loggroup]
                    )])]
            )
            cloud_trail = aws_cloudtrail.CfnTrail(
                self,
                is_logging=True,
                id=cloud_trail_config['cloud_trail_name'],
                s3_bucket_name=cloud_trail_bucket,
                cloud_watch_logs_log_group_arn=cloud_watch_loggroup,
                cloud_watch_logs_role_arn=iam_role_cloudwatch.role_arn,
                enable_log_file_validation=True,
                kms_key_id=cloud_trail_kms,
                include_global_service_events=True
            )
            # Add the resource policy as a dependancy to hopefully allow the creation of this trail
            cloud_trail.node.add_dependency(depends_on)
        naming_prefix = self.node.try_get_context("naming_prefix")
        cloud_trail_config = self.node.try_get_context("cloud_trail_config")

        create_trail = cloud_trail_config['create_trail']
        cloud_trail_name = cloud_trail_config['cloud_trail_name']

        ######################################################################
        # create cloudtrail if needed, configurable from cdk.json
        #####################################################################

        if create_trail:
            print('create kms and trail and other shit here')
            kms_config = self.node.try_get_context("kms-config")
            # Generate KMS Keys, Keys are returned as a dictionary of alias and object so it is easy to reference them
            keys = {}
            for key in kms_config['keys']:
                keys.update(create_kms(self, key))
            print(f"Keys Created {keys}")
            cloud_trail_kms = keys['cloudtrail-key'].key_arn
            cloud_trail_bucket, s3_bucket = create_s3_bucket(
                self, cloud_trail_config=cloud_trail_config, s3_bucket_key=keys['s3-bucket-key'], service_principals=["cloudtrail.amazonaws.com"])
            cloud_watch_loggroup = create_log_group(
                self, cloud_trail_config, keys['cloudwatch-key'])
            create_cloudtrail(self, cloud_trail_config, cloud_trail_bucket,
                              cloud_watch_loggroup, keys['cloudtrail-key'].key_arn, depends_on=s3_bucket)
            has_kms = True

        else:
            cloud_trail_client = boto3.client('cloudtrail')
            response = cloud_trail_client.describe_trails(
                trailNameList=[cloud_trail_name])
            try:
                trail = response['trailList'][0]
                cloud_trail_bucket = trail['S3BucketName']
                if 'KmsKeyId' in trail:
                    has_kms = True
                    cloud_trail_kms = trail['KmsKeyId']
                else:
                    has_kms = False
            except Exception as e:
                print(
                    f"Error obtaining trail information for: {cloud_trail_name}, perhaps you have the trail name wrong. Exception: {e}")
                raise SystemExit(1)

        ######################################################################
        # create IAM role for manual mod detection stack
        #####################################################################
        policy_statements = []
        policy_statements.append(
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
        )

        if has_kms:
            policy_statements.append(
                aws_iam.PolicyStatement(
                    effect=aws_iam.Effect.ALLOW,
                    actions=[
                        'kms:Decrypt',
                        'kms:DescribeKey',
                        'kms:ReEncryptFrom'
                    ],
                    resources=[
                        cloud_trail_kms
                    ]
                )
            )

        detection_inline_policies = {
            'allowS3KmsAccess': aws_iam.PolicyDocument(
                statements=policy_statements
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
