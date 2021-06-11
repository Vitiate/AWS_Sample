import boto3
import subprocess
ec2 = boto3.resource('ec2')

securityGroup = "sg-id"


release = "rhel"
major = "6"
sshUser = "root"

enableCommand = "sudo systemctl enable amazon-ssm-agent"
startCommand = "sudo systemctl start amazon-ssm-agent"

package = "https://s3.amazonaws.com/ec2-downloads-windows/SSMAgent/latest/linux_amd64/amazon-ssm-agent.rpm"
installCommand = "sudo yum install -y " + package

# only used for multi vpc accounts Filters=[{'Name': 'vpc-id', 'Values':[ vpcId ]}], 'i-id'
vpcId = "vpc-id"
# Filters=[]{'Name': 'instance-id', 'Values':[  'i-id' ]}


def sshCommand(command, user, hostname):
    run = "ssh -o StrictHostKeyChecking=no " + \
        user + "@" + hostname + " '" + command + "' "
    result = str(subprocess.getstatusoutput(run))
    return result


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
for instance in instances:
    print('Installing SSM agent via SSH')
    print(instance.id + ": Ip Address " + instance.private_ip_address)
    print(instance.id + ":   Adding Security Group " + securityGroup)
    listSgId = [sg['GroupId'] for sg in instance.security_groups]
    listSgId.append(securityGroup)
    instance.modify_attribute(Groups=listSgId)

    print(instance.id + ":   Executing " + installCommand)
    try:
        result = sshCommand(installCommand, sshUser,
                            instance.private_ip_address)
    except:
        print("Connection issue")

    print(result)

    if "Nothing to do" in result:
        print(instance.id + ":   Nothing to do, package already installed ")

    if "Complete!" in result:
        print(instance.id + ":   Installation Successful")
    print(instance.id + ":   Starting up service")
    try:
        result = sshCommand(enableCommand, sshUser,
                            instance.private_ip_address)
    except:
        print("Connection issue")
    try:
        result = sshCommand(startCommand, sshUser, instance.private_ip_address)
    except:
        print("Connection issue")
    print(instance.id + ":   Startup complete")
    print(instance.id + ":   Removing Security Group " + securityGroup)
    listSgId.remove(securityGroup)
    instance.modify_attribute(Groups=listSgId)
