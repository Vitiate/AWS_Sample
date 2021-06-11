import boto3
import subprocess
import json
import urllib.request
from botocore.exceptions import ClientError

ec2 = boto3.resource('ec2')
ec2client = boto3.client('ec2')

ip = urllib.request.urlopen('https://ident.me').read().decode('utf8')
print('My public IP address is: {}'.format(ip))
cidrIp = ip + "/32"

# The following variables are for filtering instances based on tags
release = "rhel"
major = "6"
sshUser = "root"

testCommand = ' if [ -f "/opt/aws/amazon-cloudwatch-agent/etc/log-config.json" ] ; then echo found; fi'

vpcId = ""  # Leave blank unless using an account with multiple vpcs


def createSecurityGroup(SECURITY_GROUP_NAME, DESCRIPTION, CIDR, PORT):
    response = ec2client.describe_vpcs()
    if vpcId == "":
        vpc_id = response.get('Vpcs', [{}])[0].get('VpcId', '')
    else:
        vpc_id = vpcId

    try:
        response = ec2client.create_security_group(
            GroupName=SECURITY_GROUP_NAME, Description=DESCRIPTION, VpcId=vpc_id)
        security_group_id = response['GroupId']
        print('Security Group Created %s in vpc %s.' %
              (security_group_id, vpc_id))

        data = ec2client.authorize_security_group_ingress(
            GroupId=security_group_id,
            IpPermissions=[
                {'IpProtocol': 'tcp',
                 'FromPort': PORT,
                 'ToPort': PORT,
                 'IpRanges': [{'CidrIp': CIDR}]}
            ])
        print('Ingress Successfully Set %s' % data)
    except ClientError as e:
        print(e)
    return security_group_id


def sshCommand(command, user, hostname):
    run = "ssh -o StrictHostKeyChecking=no " + \
        user + "@" + hostname + " '" + command + "' "
    status, result = subprocess.getstatusoutput(run)
    return result

# Start of Main


securityGroup = createSecurityGroup(
    "automationTempGroup", "This group created for automated run", cidrIp, 22)
if vpcId == "":
    instances = ec2.instances.filter(Filters=[
        {
            'Name': 'tag:auto:instance:os:release',
            'Values': [release]
        },
        {
            'Name': 'tag:auto:instance:os:major',
            'Values': [major]
        }
    ])
else:
    instances = ec2.instances.filter(Filters=[
        {
            'Name': 'vpc-id',
            'Values': [vpcId]
        },
        {
            'Name': 'tag:auto:instance:os:release',
            'Values': [release]
        },
        {
            'Name': 'tag:auto:instance:os:major',
            'Values': [major]
        }
    ])
for instance in instances:
    print('Updating logging tags')
    print(instance.id + ": Ip Address " + instance.private_ip_address)
    print(instance.id + ":   Adding Security Group " + securityGroup)
    listSgId = [sg['GroupId'] for sg in instance.security_groups]
    listSgId.append(securityGroup)
    instance.modify_attribute(Groups=listSgId)

    print(instance.id + ":   Executing " + testCommand)
    try:
        result = sshCommand(testCommand, sshUser, instance.private_ip_address)
    except:
        print("Connection issue")

    print(result)

    if "found" in result:
        print(instance.id + ":   Found cloudwatch log config ")
        try:
            cmd = 'cat /opt/aws/amazon-cloudwatch-agent/etc/log-config.json'
            print(instance.id + ":    Executing " + cmd)
            result = sshCommand(cmd, sshUser, instance.private_ip_address)
        except:
            print("Connection issue")
        if "log_group_name" in result:
            result = result.split("{", 1)  # Parse off any motd trash
            result = "{" + result[1]
            print(instance.id + ":    " + result)
            logConfigs = json.loads(result)
            numberOfLogs = 0
            for config in logConfigs['log_configs']:
                print(instance.id + ":   Found Log Group" +
                      config['log_group_name'])
                tagName = "auto:cloudwatch:loggroup{}".format(numberOfLogs)
                instance.create_tags(Tags=[
                    {'Key': tagName, 'Value': config['log_group_name']}
                ])
                print(instance.id + ":   Tagging complete")
                numberOfLogs += 1
    print(instance.id + ":   Removing Security Group " + securityGroup)
    listSgId.remove(securityGroup)
    instance.modify_attribute(Groups=listSgId)
print("Finished Run, delete security_group: " + securityGroup)
ec2client.delete_security_group(GroupId=securityGroup)
