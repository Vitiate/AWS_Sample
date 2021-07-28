
# Best Practices based VPC creation
This CDK project creates a best practices based VPC configured via the cdk.json file

## Configuration File

The configuration file is defined via json, you can edit the vpc-config and kms-config
sections.

### kms-config
To add additional kms keys, duplicate a key in the array and relabel for your requirements.
```json
      "keys": [
        {
          "alias": "cloudwatch-key",
          "description": "Key used by default to encrypt cloudwatch logs",
          "enable-key-rotation": true,
          "service-principles": [
            "logs.amazonaws.com"
          ]
        },
```
### vpc-config
#### Basic Configuration
```json
      "vpc-name": "accountvpc", # Name you VPC, this name will prefix other things related to your vpc
      "cidr-range": "10.98.0.0/16", # Give your vpc a cidr range, all subnets will be created in this range
      "max-az": 3, # set the number of availability zones to use in your vpc
      "nat-gateway-provider": "gateway",  # Set the nat gateway type, currently only gatway is supported
      "nat-gateways": 1, # How many nat gateways to create
```
#### Service Endpoints
Add endpoints to the array they are associated with. You can find a list of the in the AWS Console under VPC, Endpoints, Create Endpoint
```json
      "gateway-endpoints": [
        "s3",
        "dynamodb"
      ],
      "interface-endpoints": [
        "logs",
        "ssm",
        "ssmmessages",
        "secretsmanager"
      ],
```
#### Route Tables
```json
     "private-routetable": {
        "name": "private-route-table", # This name doesn't mean anything right now
        "routes": [] # Routes are added to this array. gateway-type is defined based on https://docs.aws.amazon.com/cdk/api/latest/python/aws_cdk.aws_ec2/CfnRoute.html the gateway-id is a variable within the self.vpc.{variable} within the cdk code.
      },
      "public-routetable": {
        "name": "public-route-table",
        "routes": [
          {
            "destination-cidr-block": "131.232.1.0/24",
            "gateway-type": "gateway_id",
            "gateway-id": "internet_gateway_id"
          }
        ]
      },
```
#### Subnet Config
Each subnet item will be created in every AZ.
```json
      "private-subnet-config": [
        {
          "name": "private-subnet",
          "cidr-mask": 24
        }
      ],
      "public-subnet-config": [
        {
          "name": "public-subnet",
          "cidr-mask": 24
        }
      ],
```
#### VPC Flowlog Configuration
```json
      "flowlog-config": {
        "destination": "s3",  # Destination can be s3 or cloudwatch
        "group-name": "loggroup", # Name of the log group if destination is cloudwatch
        "bucket-name": "flow-logs", # S3 bucket name if destination is s3
        "traffic_type": "ALL" # What to log based on API settings
      }
```
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
