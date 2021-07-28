from aws_cdk import core as cdk
from aws_cdk import core
import hashlib
import aws_cdk.aws_ec2 as aws_ec2
import aws_cdk.aws_s3 as aws_s3
import aws_cdk.aws_logs as aws_logs
import aws_cdk.aws_kms as aws_kms
import aws_cdk.aws_iam as aws_iam


class DefaultAccountDeployStack(cdk.Stack):

    def __init__(self, scope: cdk.Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # Grab the configuration for the vpc
        vpc_config = self.node.try_get_context("vpc-config")

        # Create the base kms managed keys for s3 and loggroup encryption
        kms_config = self.node.try_get_context("kms-config")
        keys = []  # Collect the key's for later use
        for key in kms_config['keys']:
            print(f"Create {key['alias']}")
            kms_key = aws_kms.Key(self,
                                  id=key['alias'],
                                  alias=key['alias'],
                                  description=key['description'],
                                  enabled=True,
                                  enable_key_rotation=key['enable-key-rotation']
                                  )
            if key['alias'] == "s3-bucket-key":
                s3_bucket_key = kms_key
            if key['alias'] == "cloudwatch-key":
                cloudwatch_key = kms_key

            for principle in key['service-principles']:
                print(f"Grant E/D to on {key['alias']} to {principle}")
                iam_principle = aws_iam.ServicePrincipal(service=principle)
                kms_key.grant_encrypt_decrypt(iam_principle)

        # Grab the flowlog config, if we have to, create a s3 bucket
        try:
            flowlog_config = vpc_config["flowlog-config"]
            flowlog_enabled = True
            if flowlog_config["destination"] == "s3":

                s3_bucketname = f"{vpc_config['vpc-name']}-{flowlog_config['bucket-name']}"
                s3_hash = hash(s3_bucketname) % 10**8
                s3_bucketname = f"{s3_bucketname}-{s3_hash}"

                # create s3 bucket
                block_pub = aws_s3.BlockPublicAccess(
                    block_public_acls=True,
                    ignore_public_acls=True,
                    block_public_policy=True,
                    restrict_public_buckets=True
                )
                s3_bucket = aws_s3.Bucket(
                    self, 'S3BucketForVPCFlowLogs', block_public_access=block_pub,
                    bucket_name=s3_bucketname,
                    removal_policy=core.RemovalPolicy.DESTROY,
                    encryption_key=s3_bucket_key,
                    encryption=aws_s3.BucketEncryption('KMS')
                )
                flowlog_destination = aws_ec2.FlowLogDestination.to_s3(
                    s3_bucket)

            if flowlog_config["destination"] == "cloudwatch":
                loggroup_name = f"{vpc_config['vpc-name']}-{flowlog_config['group-name']}"
                flowlog_loggroup = aws_logs.LogGroup(
                    self, log_group_name=loggroup_name, encryption_key=cloudwatch_key)
                flowlog_destination = aws_ec2.FlowLogDestination.to_cloud_watch_logs(
                    flowlog_loggroup)
        except:
            flowlog_enabled = False
            flowlog_destination = None

        # Setup the subnet configuration
        private_subnet_config = vpc_config["private-subnet-config"]
        public_subnet_config = vpc_config["public-subnet-config"]
        subnet_configuration = []

        for subnet in private_subnet_config:
            # Build the private subnet as isolated to keep from autogenerating nat gateways.
            print(subnet)
            subnet_configuration.append(aws_ec2.SubnetConfiguration(
                subnet_type=aws_ec2.SubnetType('PRIVATE'),
                name=subnet["name"],
                cidr_mask=subnet["cidr-mask"]
            ))
        for subnet in public_subnet_config:
            print(subnet)
            subnet_configuration.append(aws_ec2.SubnetConfiguration(
                subnet_type=aws_ec2.SubnetType('PUBLIC'),
                name=subnet["name"],
                cidr_mask=subnet["cidr-mask"]
            ))
        print(subnet_configuration)

        # Provisioning VPC
        self.vpc = aws_ec2.Vpc(self,
                               id=vpc_config["vpc-name"],
                               cidr=vpc_config["cidr-range"],
                               max_azs=vpc_config["max-az"],
                               subnet_configuration=subnet_configuration,
                               nat_gateways=vpc_config['nat-gateways']
                               )
        self.vpc_id = self.vpc.vpc_id

        print("vpc in")
        if flowlog_enabled:
            self.vpc.add_flow_log(
                id="flowlog",
                destination=flowlog_destination,
                traffic_type=aws_ec2.FlowLogTrafficType(
                    flowlog_config['traffic_type'])
            )
        print("flowlog in")

        public_routetable_config = vpc_config['public-routetable']
        private_routetable_config = vpc_config['private-routetable']
       # Create routes on Route tables
        print("Create the public routes ")
        id = 1
        print(public_routetable_config)
        for subnet in self.vpc.public_subnets:
            for route in public_routetable_config['routes']:
                id = id + 1
                aws_ec2.CfnRoute(
                    self,
                    id=f"public-route-{id}",
                    route_table_id=subnet.route_table.route_table_id,
                    destination_cidr_block=route['destination-cidr-block'],
                    **{route['gateway-type']: getattr(self.vpc, route['gateway-id'])}
                )

        print("Create the private routes ")
        id = 0
        print(private_routetable_config)
        for subnet in self.vpc.public_subnets:
            for route in public_routetable_config['routes']:
                id = id + 1
                aws_ec2.CfnRoute(
                    self,
                    id=f"public-route-{id}",
                    route_table_id=subnet.route_table.route_table_id,
                    destination_cidr_block=route['destination-cidr-block'],
                    **{route['gateway-type']: getattr(self.vpc, route['gateway-id'])}
                )


#        ############################
#        # Gateway Endpoints        #
#        ############################
        gateway_endpoints = vpc_config['gateway-endpoints']
        for endpoint in gateway_endpoints:
            aws_ec2.GatewayVpcEndpoint(
                self,
                id=f"{endpoint}",
                service=aws_ec2.GatewayVpcEndpointAwsService(endpoint),
                subnets=self.vpc.private_subnets,
                vpc=self.vpc
            )

#        ############################
#        # Interface Endpoints      #
#        ############################
        interface_endpoints = vpc_config['interface-endpoints']
        for endpoint in interface_endpoints:
            aws_ec2.InterfaceVpcEndpoint(
                self,
                id=f"{endpoint}",
                service=aws_ec2.InterfaceVpcEndpointAwsService(endpoint),
                vpc=self.vpc
            )
