#!/usr/bin/env python3
# Jeremy Tirrell 2021

import os
import subprocess
from aws_cdk import core
from aws_cdk.core import Tags


from event_bridge_shipper.event_bridge_shipper_stack import EventBridgeShipperStack

app = core.App()
EventBridgeShipperStack(app, "aes-siem-eventbridge-shipper",
                        description="SIEM on Amazon ES Event Bridge Shipper")

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
print(app)
