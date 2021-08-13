
# Welcome to your CDK Python project!

# To execute
Install the sub packages for the lambda
```
bash ./install-lambda-resource-modules.sh
```
Bootstrap the cdk
```
cdk bootstrap
```

deploy the cdk, try a dry run first to verify that everything is setup properly
```
cdk synth
cdk deploy

```
# To configure
Edit the cdk.json

# cdk.json configuration

```
    "env_slack_webhook_url": "https://hooks.slack.com/services/<SLACKWEBHOOK>", # Enter your slack webhook url or no_value
    "env_sns_topic": "no_value",                  # Enter your sns-topic or no_value
    "cloud_trail_config": {
      "create_trail": false,                      # Setting this to true will deploy a best practices compliant, cloudtrail, bucket, loggroup and all the required kms keys with appropriate permissions
      "cloud_trail_name": "cloudtrail-event-log", # Enter the name of the cloudtrail to monitor for management events, this cloudtrail should exist, if it does not exist set the create_trail varaible to true
      "cloud_trail_bucket": "test-bucket",        # Name of the s3 bucket to create. This is ignored if not creating a trail
      "cloud_trail_data_events": true,            # If true will also log data events to the trail. This is ignored if not creating a trail
      "cloud_watch_log_group": "test-loggroup"    # Name of the log group to create. This is ignored if not creating a trail
    },
    "kms-config": {
      "keys": [ # KMS keys are configured here, do not change the defaults or their alias's, this will break the cdk. This is ignored if not creating a trail
        {
          "alias": "cloudtrail-key",
          "description": "Key used to encrypt cloudtrail",
          "enable-key-rotation": true,
          "service-principles": [
            "cloudtrail.amazonaws.com"
          ]
        },
        {
          "alias": "cloudwatch-key",
          "description": "Key used by default to encrypt cloudwatch logs",
          "enable-key-rotation": true,
          "service-principles": [
            "logs.amazonaws.com",
            "cloudtrail.amazonaws.com"
          ]
        },
        {
          "alias": "s3-bucket-key",
          "description": "Key used to encrypt cloudtrail s3 bucket",
          "enable-key-rotation": true,
          "service-principles": [
            "s3.amazonaws.com",
            "cloudtrail.amazonaws.com",
            "lambda.amazonaws.com"
          ]
        }
      ]
    }
  }
}
```

This is a blank project for Python development with CDK.

The `cdk.json` file tells the CDK Toolkit how to execute your app.

This project is set up like a standard Python project.  The initialization
process also creates a virtualenv within this project, stored under the `.venv`
directory.  To create the virtualenv it assumes that there is a `python3`
(or `python` for Windows) executable in your path with access to the `venv`
package. If for any reason the automatic creation of the virtualenv fails,
you can create the virtualenv manually.

To manually create a virtualenv on MacOS and Linux:

```
$ python3 -m venv .venv
```

After the init process completes and the virtualenv is created, you can use the following
step to activate your virtualenv.

```
$ source .venv/bin/activate
```

If you are a Windows platform, you would activate the virtualenv like this:

```
% .venv\Scripts\activate.bat
```

Once the virtualenv is activated, you can install the required dependencies.

```
$ pip install -r requirements.txt
```

At this point you can now synthesize the CloudFormation template for this code.

```
$ cdk synth
```

To add additional dependencies, for example other CDK libraries, just add
them to your `setup.py` file and rerun the `pip install -r requirements.txt`
command.

## Useful commands

 * `cdk ls`          list all stacks in the app
 * `cdk synth`       emits the synthesized CloudFormation template
 * `cdk deploy`      deploy this stack to your default AWS account/region
 * `cdk diff`        compare deployed stack with current state
 * `cdk docs`        open CDK documentation

Enjoy!
