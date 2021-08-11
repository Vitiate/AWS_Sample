#!/usr/bin/env python3
import os
import subprocess
from aws_cdk import core as cdk
from aws_cdk.core import Tags
from aws_cdk import core

from console_change_notification.console_change_notification_stack import ConsoleChangeNotificationStack


app = core.App()
ConsoleChangeNotificationStack(app, "ConsoleChangeNotificationStack")

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
