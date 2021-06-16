#!/usr/bin/env python3
import os
from aws_cdk import core as cdk
import subprocess
from aws_cdk.core import Tags

from aws_cdk import core

from source.source_stack import SourceStack


app = core.App()
SourceStack(app, "CFN-Drift-Notification",
            description="Deploys a cloudformation drift monitor that can revert drifted changes to tagged stack"
            )

# Apply git repo tags to all objects in stack
try:
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
    Tags.of(app).add(key="aes:git:repository", value=origin)
    Tags.of(app).add(key="aes:git:description", value=label)
except:
    print("No Git Repo information found")

app.synth()
