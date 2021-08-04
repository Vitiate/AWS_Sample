#!/usr/bin/env python3
import os
import boto3
import subprocess
from aws_cdk.core import Tags
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

    print("Obtaining repo info for tagging")
    label = str(subprocess.check_output(
        ["git",  "describe", "--always"]))
    origin = str(subprocess.check_output(
        ["git", "config", "--get", "remote.origin.url"]))

    origin = origin.split('\'')[1]
    label = label.split('\'')[1]

    origin = origin.rstrip('\\n')
    label = label.rstrip('\\n')
    print(f"Origin: {origin}")
    print(f"Description: {label}")
    Tags.of(app).add(key="git:repository", value=origin)
    Tags.of(app).add(key="git:description", value=label)
    tag_config = app.node.try_get_context("tags")
    print(tag_config)
    for tag in tag_config:
        Tags.of(app).add(key=tag['Key'], value=tag['Value'])
    app.synth()

    app.synth()
except Exception as e:
    print(f"Error {e}")
