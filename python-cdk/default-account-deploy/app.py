#!/usr/bin/env python3
import os
import boto3
from aws_cdk import core as cdk

# For consistency with TypeScript code, `cdk` is the preferred import name for
# the CDK's core module.  The following line also imports it as `core` for use
# with examples from the CDK Developer's Guide, which are in the process of
# being updated to use `cdk`.  You may delete this import if you don't need it.
from aws_cdk import core

from default_account_deploy.default_account_deploy_stack import DefaultAccountDeployStack
try:
    client = boto3.client("sts")
    account_id = client.get_caller_identity()["Account"]
    region = os.environ['AWS_REGION']
    app = core.App()
    print(f"Running in {account_id}/{region}")
    env = {"account": account_id, "region": region}
    DefaultAccountDeployStack(app, "DefaultAccountDeployStack", env=env)

    app.synth()
except Exception as e:
    print(f"Error {e}")
