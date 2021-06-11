# s3 Public Block Remediation

# Purpose
This repository contains the code required to auto-remidiate s3 buckets. The code watches for the
creation of a bucket that does not have the public access block enabled. If a bucket is created
like this it checks the bucket for a definable tag that identifes the bucket as excluded. If this 
tag does not exist the public access block is applied to the bucket.

# Function
The Lambda scripts and templates contained within will create cloudwatch rules to trigger on the 
creation of a s3 bucket.

# Bypass
To bypass the s3 auto-remidiation add the tag defined in the template.yaml to the s3 bucket.

# Configuration
Edit the cfn-cli.yaml file and add the slack web hook to send notifications to the correct Slack channel or add a SNS queue. In addtion you should set a TestTag to search for when excluding buckets.
