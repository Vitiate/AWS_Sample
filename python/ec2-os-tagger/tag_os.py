import boto3
import subprocess
ec2 = boto3.resource('ec2')

securityGroup = "sg-id"

# only used for multi vpc accounts Filters=[{'Name': 'vpc-id', 'Values':[ vpcId ]}],
vpcId = "vpc-ID"
# Filters=[]{'Name': 'vpc-id', 'Values':[  '' ]}
instances = ec2.instances.filter()
for instance in instances:

    print(instance.id + ": Ip Address " + instance.private_ip_address)
    print(instance.id + ":   Platform: " + str(instance.platform))
    if str(instance.platform) != "windows":
        print(instance.id + ":   Adding Security Group " + securityGroup)
        listSgId = [sg['GroupId'] for sg in instance.security_groups]
        listSgId.append(securityGroup)
        instance.modify_attribute(Groups=listSgId)
        command = "ssh -o StrictHostKeyChecking=no " + \
            instance.private_ip_address + " 'cat /etc/*release'"
        print(instance.id + ":   Executing " + command)
        try:
            result = str(subprocess.getstatusoutput(command))
            if "ec2-user" in result:
                print(instance.id + ":   Executing failed due to ec2-user requirement")
                command = "ssh -o StrictHostKeyChecking=no ec2-user@" + \
                    instance.private_ip_address + " 'cat /etc/*release'"
                print(instance.id + ":   Executing " + command)
                try:
                    result = str(subprocess.getstatusoutput(command))
                except:
                    print("Connection timed out")
        except:
            print("Connection timed out")

        print(instance.id + ":   Removing Security Group " + securityGroup)
        listSgId.remove(securityGroup)
        instance.modify_attribute(Groups=listSgId)
        if "(255," not in result:
            print(instance.id + ":   Result - " + result)

            releaseString = result.split("release ", 1)[1]
            print(instance.id + ":   Release String - " + releaseString)

            if "Red Hat" in result:
                release = "rhel"
            if "amzn" in result:
                release = "amzn"
            print(instance.id + ":   Release - " + release)

            releaseVersion = releaseString.split(" ", 1)[0]
            print(instance.id + ":   Version - " + releaseVersion)

            majorVersion = releaseVersion.split(".", 1)[0]
            try:
                minorVersion = releaseVersion.split(".", 1)[1]
            except:
                minorVersion = "0"
            print(instance.id + ":   Major Version - " + majorVersion)
            print(instance.id + ":   Minor Version - " + minorVersion)

            print(instance.id + ":   Attaching Tags")
            instance.create_tags(Tags=[
                {'Key': 'auto:instance:os:release', 'Value': release},
                {'Key': 'auto:instance:os:major', 'Value': majorVersion},
                {'Key': 'auto:instance:os:minor', 'Value': minorVersion},
            ])
        else:
            print(instance.id + ":   Bypassed Powered off or Windows instance")
    else:
        print(instance.id + ":   Unable to login to instance")
