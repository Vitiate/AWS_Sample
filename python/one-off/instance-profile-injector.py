import boto3
import logging
listOfManaged = [
    'SecretsManagerReadWrite',
    'CloudWatchAgentServerPolicy',
    'AmazonSSMManagedInstanceCore',
    'AmazonS3ReadOnlyAccess'
]


def lambda_handler(event, context):
    iam = boto3.client('iam')
    logger = logging.getLogger()
    logger.setLevel(logging.WARNING)
    # Get a list of all instance profiles
    instance_profiles = iam.list_instance_profiles(PathPrefix="/")
    policiesAttached = 0
    profilesTested = 0
    # Check all the profiles for attached IAM policies
    for profiles in instance_profiles['InstanceProfiles']:
        profilesTested += 1
        for role in profiles['Roles']:
            rolePolicies = iam.list_attached_role_policies(
                RoleName=role['RoleName'])
            # Generate a list of attached policies
            policyList = []
            for p in rolePolicies['AttachedPolicies']:
                policyList.append(p['PolicyName'])
            # Check if the list of managed policies exists in the attached policies of the instance profiles
            for mp in listOfManaged:
                if mp not in policyList:
                    policy_arn = f'arn:aws:iam::aws:policy/{mp}'
                    iam.attach_role_policy(
                        RoleName=role['RoleName'], PolicyArn=policy_arn)
                    print(profiles['InstanceProfileName'] +
                          f" Attach policy {policy_arn} to " + role['RoleName'])
                    logger.info(profiles['InstanceProfileName'] +
                                f" Attach policy {policy_arn} to " + role['RoleName'])
                    policiesAttached += 1
    return {
        'statusCode': 200,
        'body': f"Attached {policiesAttached} Tested {profilesTested} profiles"
    }
