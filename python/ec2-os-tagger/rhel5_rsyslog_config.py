import boto3
import subprocess
ec2 = boto3.resource('ec2')


securityGroup = "sg-id"

release = "rhel"
major = "5"
sshUser = "root"

commandArray = [
    'echo "authpriv.*          @@syslog.server.com:5140" >> /etc/rsyslog.conf',
    'echo "auth.*              @@syslog.server.com:5140" >> /etc/rsyslog.conf',
    'echo "*.emerg             @@syslog.server.com:5140" >> /etc/rsyslog.conf',
    'echo "cron.warn           @@syslog.server.com:5140" >> /etc/rsyslog.conf',
    'echo "yum.*               @@syslog.server.com:5140" >> /etc/rsyslog.conf',
    'echo "ntp.warn            @@syslog.server.com:5140" >> /etc/rsyslog.conf',
    'semanage port -a -t syslogd_port_t -p tcp 5140'
]

testCommand = ' if $(grep -q "syslog.server.com" /etc/rsyslog.conf); then echo found; fi'
startCommand = "service reload rsyslog"

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
    print('Updating RSyslog via SSH')
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
        print(instance.id + ":   Nothing to do, found existing syslog config ")
    else:
        print(instance.id + ":    Updating syslog config")
        try:
            for cmd in commandArray:
                print(instance.id + ":    Executing " + cmd)
                result = sshCommand(cmd, sshUser, instance.private_ip_address)
                print(instance.id + ":    " + result)
        except:
            print("Connection issue")

        try:
            print(instance.id + ":    Executing " + startCommand)
            result = sshCommand(startCommand, sshUser,
                                instance.private_ip_address)
        except:
            print("Connection issue")

    print(instance.id + ":   Startup complete")
    print(instance.id + ":   Removing Security Group " + securityGroup)
    listSgId.remove(securityGroup)
    instance.modify_attribute(Groups=listSgId)
