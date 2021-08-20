#!/usr/bin/env python3
#
# Licensed under the Apache 2.0 and MITnoAttr License.
#
# Copyright 2020 Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License"). You may not use this file except in compliance with the License. A copy of the License is located at
# https://aws.amazon.com/apache2.0/
 

import botocore
import boto3
import json
import datetime
import logging
import jmespath
import base64
from pkg_resources import CHECKOUT_DIST, packaging


__author__ = "Jeremy Tirrell"
__email__ = "jtirrell@amazon.com"
__copyright__ = "Copyright 2021 Amazon.com, Inc. or its affiliates. All Rights Reserved."
__credits__ = ["Jeremy Tirrell"]

# Default region listed here
REGION_NAME = "us-west-2"
blankjson = {}
response = ""

# Setup Logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s.%(msecs)03d %(levelname)s %(module)s - %(funcName)s: %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
)

logger = logging.getLogger()
logging.getLogger('boto3').setLevel(logging.CRITICAL)
logging.getLogger('botocore').setLevel(logging.CRITICAL)
logging.getLogger('s3transfer').setLevel(logging.CRITICAL)
logging.getLogger('urllib3').setLevel(logging.CRITICAL)


# Helper class to convert a datetime item to JSON.
class DateTimeEncoder(json.JSONEncoder):
    def default(self, z):
        if isinstance(z, datetime.datetime):
            return (str(z))
        else:
            return super().default(z)


def CreateNewWorkload(
    waclient,
    workloadName,
    description,
    reviewOwner,
    environment,
    awsRegions,
    lenses
):

    # Create your workload
    try:
        waclient.create_workload(
            WorkloadName=workloadName,
            Description=description,
            ReviewOwner=reviewOwner,
            Environment=environment,
            AwsRegions=awsRegions,
            Lenses=lenses
        )
    except waclient.exceptions.ConflictException as e:
        workloadId = FindWorkload(waclient, workloadName)
        logger.error("ERROR - The workload name %s already exists as workloadId %s" %
                     (workloadName, workloadId))
    except botocore.exceptions.ParamValidationError as e:
        logger.error("ERROR - Parameter validation error: %s" % e)
    except botocore.exceptions.ClientError as e:
        logger.error("ERROR - Unexpected error: %s" % e)


def FindWorkload(
    waclient,
    workloadName
):

    # Finding your WorkloadId
    try:
        response = waclient.list_workloads(
            WorkloadNamePrefix=workloadName
        )
    except botocore.exceptions.ParamValidationError as e:
        logger.error("ERROR - Parameter validation error: %s" % e)
    except botocore.exceptions.ClientError as e:
        logger.error("ERROR - Unexpected error: %s" % e)

    # print("Full JSON:",json.dumps(response['WorkloadSummaries'], cls=DateTimeEncoder))
    workloadId = response['WorkloadSummaries'][0]['WorkloadId']
    # print("WorkloadId",workloadId)
    return workloadId


def DeleteWorkload(
    waclient,
    workloadId
):

    # Delete the WorkloadId
    try:
        response = waclient.delete_workload(
            WorkloadId=workloadId
        )
    except botocore.exceptions.ParamValidationError as e:
        logger.error("ERROR - Parameter validation error: %s" % e)
    except botocore.exceptions.ClientError as e:
        logger.error("ERROR - Unexpected error: %s" % e)


def GetWorkload(
    waclient,
    workloadId
):

    # Get the WorkloadId
    try:
        response = waclient.get_workload(
            WorkloadId=workloadId
        )
    except botocore.exceptions.ParamValidationError as e:
        logger.error("ERROR - Parameter validation error: %s" % e)
    except botocore.exceptions.ClientError as e:
        logger.error("ERROR - Unexpected error: %s" % e)

    # print("Full JSON:",json.dumps(response['Workload'], cls=DateTimeEncoder))
    workload = response['Workload']
    # print("WorkloadId",workloadId)
    return workload


def disassociateLens(
    waclient,
    workloadId,
    lens
):

    # Disassociate the lens from the WorkloadId
    try:
        response = waclient.disassociate_lenses(
            WorkloadId=workloadId,
            LensAliases=lens
        )
    except botocore.exceptions.ParamValidationError as e:
        logger.error("ERROR - Parameter validation error: %s" % e)
    except botocore.exceptions.ClientError as e:
        logger.error("ERROR - Unexpected error: %s" % e)


def associateLens(
    waclient,
    workloadId,
    lens
):

    # Associate the lens from the WorkloadId
    try:
        response = waclient.associate_lenses(
            WorkloadId=workloadId,
            LensAliases=lens
        )
    except botocore.exceptions.ParamValidationError as e:
        logger.error("ERROR - Parameter validation error: %s" % e)
    except botocore.exceptions.ClientError as e:
        logger.error("ERROR - Unexpected error: %s" % e)


def listLens(
    waclient
):

    # List all lenses currently available
    try:
        response = waclient.list_lenses()
    except botocore.exceptions.ParamValidationError as e:
        logger.error("ERROR - Parameter validation error: %s" % e)
    except botocore.exceptions.ClientError as e:
        logger.error("ERROR - Unexpected error: %s" % e)

    # print(json.dumps(response))
    lenses = jmespath.search("LensSummaries[*].LensAlias", response)

    return lenses


def findQuestionId(
    waclient,
    workloadId,
    lensAlias,
    pillarId,
    questionTitle
):

    # Find a questionID using the questionTitle
    try:
        response = waclient.list_answers(
            WorkloadId=workloadId,
            LensAlias=lensAlias,
            PillarId=pillarId
        )
    except botocore.exceptions.ParamValidationError as e:
        logger.error("ERROR - Parameter validation error: %s" % e)
    except botocore.exceptions.ClientError as e:
        logger.error("ERROR - Unexpected error: %s" % e)

    answers = response['AnswerSummaries']
    while "NextToken" in response:
        response = waclient.list_answers(
            WorkloadId=workloadId, LensAlias=lensAlias, PillarId=pillarId, NextToken=response["NextToken"])
        answers.extend(response["AnswerSummaries"])

    jmesquery = "[?starts_with(QuestionTitle, `" + \
        questionTitle+"`) == `true`].QuestionId"
    questionId = jmespath.search(jmesquery, answers)

    return questionId[0]


def findChoiceId(
    waclient,
    workloadId,
    lensAlias,
    questionId,
    choiceTitle,
):

    # Find a choiceId using the choiceTitle
    try:
        response = waclient.get_answer(
            WorkloadId=workloadId,
            LensAlias=lensAlias,
            QuestionId=questionId
        )
    except botocore.exceptions.ParamValidationError as e:
        logger.error("ERROR - Parameter validation error: %s" % e)
    except botocore.exceptions.ClientError as e:
        logger.error("ERROR - Unexpected error: %s" % e)

    jmesquery = "Answer.Choices[?starts_with(Title, `" + \
        choiceTitle+"`) == `true`].ChoiceId"
    choiceId = jmespath.search(jmesquery, response)

    return choiceId[0]


def getAnswersForQuestion(
    waclient,
    workloadId,
    lensAlias,
    questionId
):

    # Find a answer for a questionId
    try:
        response = waclient.get_answer(
            WorkloadId=workloadId,
            LensAlias=lensAlias,
            QuestionId=questionId
        )
    except botocore.exceptions.ParamValidationError as e:
        logger.error("ERROR - Parameter validation error: %s" % e)
    except botocore.exceptions.ClientError as e:
        logger.error("ERROR - Unexpected error: %s" % e)

    # print(json.dumps(response))
    jmesquery = "Answer.SelectedChoices"
    answers = jmespath.search(jmesquery, response)
    # print(answers)
    return answers


def updateAnswersForQuestion(
    waclient,
    workloadId,
    lensAlias,
    questionId,
    selectedChoices,
    notes
):
    # Update a answer to a question
    ChoiceUpdates = {}
    for choice in selectedChoices:
        ChoiceUpdates[choice] = {'Status': 'SELECTED'}
    try:
        ChoiceUpdates = {}
        for choice in selectedChoices:
            ChoiceUpdates[choice] = {'Status': 'SELECTED'}
        response = waclient.update_answer(
            WorkloadId=workloadId,
            LensAlias=lensAlias,
            QuestionId=questionId,
            ChoiceUpdates=ChoiceUpdates,
            SelectedChoices=selectedChoices,
            Notes=notes
        )
    except botocore.exceptions.ParamValidationError as e:
        logger.error("ERROR - Parameter validation error: %s" % e)
    except botocore.exceptions.ClientError as e:
        logger.error("ERROR - Unexpected error: %s" % e)

    jmesquery = "Answer.SelectedChoices"
    answers = jmespath.search(jmesquery, response)
    return answers


def listMilestones(
    waclient,
    workloadId
):

    # Find a milestone for a workloadId
    try:
        response = waclient.list_milestones(
            WorkloadId=workloadId,
            MaxResults=50  # Need to check why I am having to pass this parameter
        )
    except botocore.exceptions.ParamValidationError as e:
        logger.error("ERROR - Parameter validation error: %s" % e)
    except botocore.exceptions.ClientError as e:
        logger.error("ERROR - Unexpected error: %s" % e)
    # print("Full JSON:",json.dumps(response['MilestoneSummaries'], cls=DateTimeEncoder))
    milestoneNumber = response['MilestoneSummaries']
    return milestoneNumber


def createMilestone(
    waclient,
    workloadId,
    milestoneName
):

    # Create a new milestone with milestoneName
    try:
        response = waclient.create_milestone(
            WorkloadId=workloadId,
            MilestoneName=milestoneName
        )
    except waclient.exceptions.ConflictException as e:
        milestones = listMilestones(waclient, workloadId)
        jmesquery = "[?starts_with(MilestoneName,`" + \
            milestoneName+"`) == `true`].MilestoneNumber"
        milestoneNumber = jmespath.search(jmesquery, milestones)
        logger.error("ERROR - The milestone name %s already exists as milestone %s" %
                     (milestoneName, milestoneNumber))
        return milestoneNumber[0]
    except botocore.exceptions.ParamValidationError as e:
        logger.error("ERROR - Parameter validation error: %s" % e)
    except botocore.exceptions.ClientError as e:
        logger.error("ERROR - Unexpected error: %s" % e)

    # print("Full JSON:",json.dumps(response['MilestoneSummaries'], cls=DateTimeEncoder))
    milestoneNumber = response['MilestoneNumber']
    return milestoneNumber


def getMilestone(
    waclient,
    workloadId,
    milestoneNumber
):

    # Use get_milestone to return the milestone structure
    try:
        response = waclient.get_milestone(
            WorkloadId=workloadId,
            MilestoneNumber=milestoneNumber
        )
    except botocore.exceptions.ParamValidationError as e:
        logger.error("ERROR - Parameter validation error: %s" % e)
    except botocore.exceptions.ClientError as e:
        logger.error("ERROR - Unexpected error: %s" % e)

    # print("Full JSON:",json.dumps(response['Milestone'], cls=DateTimeEncoder))
    milestoneResponse = response['Milestone']
    return milestoneResponse


def getMilestoneRiskCounts(
    waclient,
    workloadId,
    milestoneNumber
):

    # Return just the RiskCount for a particular milestoneNumber

    milestone = getMilestone(waclient, workloadId, milestoneNumber)
    # print("Full JSON:",json.dumps(milestone['Workload']['RiskCounts'], cls=DateTimeEncoder))
    milestoneRiskCounts = milestone['Workload']['RiskCounts']
    return milestoneRiskCounts


def listAllAnswers(
    waclient,
    workloadId,
    lensAlias,
    milestoneNumber=""
):

    # Get a list of all answers
    try:
        if milestoneNumber:
            response = waclient.list_answers(
                WorkloadId=workloadId,
                LensAlias=lensAlias,
                MilestoneNumber=milestoneNumber
            )
        else:
            response = waclient.list_answers(
                WorkloadId=workloadId,
                LensAlias=lensAlias
            )

    except botocore.exceptions.ParamValidationError as e:
        logger.error("ERROR - Parameter validation error: %s" % e)
    except botocore.exceptions.ClientError as e:
        logger.error("ERROR - Unexpected error: %s" % e)

    answers = response['AnswerSummaries']
    while "NextToken" in response:
        if milestoneNumber:
            response = waclient.list_answers(
                WorkloadId=workloadId, LensAlias=lensAlias, MilestoneNumber=milestoneNumber, NextToken=response["NextToken"])
        else:
            response = waclient.list_answers(
                WorkloadId=workloadId, LensAlias=lensAlias, NextToken=response["NextToken"])
        answers.extend(response["AnswerSummaries"])

    # print("Full JSON:",json.dumps(answers, cls=DateTimeEncoder))
    return answers


def getLensReview(
    waclient,
    workloadId,
    lensAlias,
    milestoneNumber=""
):

    # Use get_lens_review to return the lens review structure
    try:
        if milestoneNumber:
            response = waclient.get_lens_review(
                WorkloadId=workloadId,
                LensAlias=lensAlias,
                MilestoneNumber=milestoneNumber
            )
        else:
            response = waclient.get_lens_review(
                WorkloadId=workloadId,
                LensAlias=lensAlias
            )

    except botocore.exceptions.ParamValidationError as e:
        logger.error("ERROR - Parameter validation error: %s" % e)
    except botocore.exceptions.ClientError as e:
        logger.error("ERROR - Unexpected error: %s" % e)

    # print("Full JSON:",json.dumps(response['LensReview'], cls=DateTimeEncoder))
    lensReview = response['LensReview']
    return lensReview


def getLensReviewPDFReport(
    waclient,
    workloadId,
    lensAlias,
    milestoneNumber=""
):

    # Use get_lens_review_report to return the lens review PDF in base64 structure
    try:
        if milestoneNumber:
            response = waclient.get_lens_review_report(
                WorkloadId=workloadId,
                LensAlias=lensAlias,
                MilestoneNumber=milestoneNumber
            )
        else:
            response = waclient.get_lens_review_report(
                WorkloadId=workloadId,
                LensAlias=lensAlias
            )

    except botocore.exceptions.ParamValidationError as e:
        logger.error("ERROR - Parameter validation error: %s" % e)
    except botocore.exceptions.ClientError as e:
        logger.error("ERROR - Unexpected error: %s" % e)

    # print("Full JSON:",json.dumps(response['LensReviewReport']['Base64String'], cls=DateTimeEncoder))
    lensReviewPDF = response['LensReviewReport']['Base64String']
    return lensReviewPDF


def test_root_mfa():
    # Find out if the root aws account has MFA
    logger.info("Looking for MFA")
    iam_client = boto3.client("iam")
    if iam_client.get_account_summary()['SummaryMap']['AccountMFAEnabled']:
        logger.info("Found root MFA")
        return True
    else:
        logger.info("No MFA found")
        return False


def test_root_access_keys():
    # Find out if the root account has access keys attached
    logger.info("Looking for access keys")
    iam_client = boto3.client("iam")
    if iam_client.get_account_summary()['SummaryMap']['AccountAccessKeysPresent'] < 1:
        logger.info("No access keys found")
        return True
    else:
        logger.info("Found root account access keys")
        return False


def test_organization():
    # Find out if the root account has access keys attached
    logger.info("Looking for organization")
    organizations_client = boto3.client("organizations")
    if len(organizations_client.describe_organization()['Organization']['Id']) > 1:
        logger.info("Found an OrgId")
        return True
    else:
        logger.info("Account not in Org")
        return False

def check_mfa(res_users):
  # Check users for mfa
  iam_client = boto3.client('iam')
  result = True
  for user in res_users:
    userMfa = iam_client.list_mfa_devices(UserName = user['UserName'])
    if len(userMfa['MFADevices']) > 0:
      print(f"Found MFA device for {user['UserName']}")
    else:
      print(f"No MFA device for {user['UserName']}")
      result = False
  return result

def test_user_mfa():
  # Test to ensure every user has an MFA attached, a single user fails the test
    iam_client = boto3.client('iam')
    max_items = 50
    try:
        res_users = iam_client.list_users(
            MaxItems=max_items
        )
        if not check_mfa(res_users['Users']):
          return False
    except Exception as error:
        print(f'An error occurred while fetching user list. {error}')
        return
    if res_users['IsTruncated']:
        while res_users['IsTruncated']:
            marker = res_users['Marker']
            try:
                res_users = iam_client.list_users(
                    Marker=marker,
                    MaxItems=max_items
                )

                if not check_mfa(res_users):
                  return False
            except Exception as error:
                print(f'An error occurred while fetching user list. {error}')
    return True


def main():
    boto3_min_version = "1.18.26"
    # Verify if the version of Boto3 we are running has the wellarchitected APIs included
    print(f"Boto: {boto3.__version__}")
    if (packaging.version.parse(boto3.__version__) < packaging.version.parse(boto3_min_version)):
        logger.error("Your Boto3 version (%s) is less than %s. You must ugprade to run this script (pip3 upgrade boto3)" % (
            boto3.__version__, boto3_min_version))
        exit()

    # STEP 1 - Configure environment
    logger.info("1 - Starting Boto %s Session" % boto3.__version__)
    # Create a new boto3 session
    SESSION = boto3.session.Session()
    # Initiate the well-architected session using the region defined above
    WACLIENT = SESSION.client(
        service_name='wellarchitected',
        region_name=REGION_NAME,
    )

    WORKLOADNAME = 'WA Test Workload'
    DESCRIPTION = 'Test Workload'
    REVIEWOWNER = 'Jeremy Tirrell'
    ENVIRONMENT = 'PRODUCTION'
    AWSREGIONS = [REGION_NAME]
    LENSES = ['wellarchitected', 'foundationaltechnicalreview']

    # STEP 2 - Creating a workload
    #  https://wellarchitectedlabs.com/well-architectedtool/200_labs/200_using_awscli_to_manage_wa_reviews/2_create_workload/
    logger.info(
        "2 - Creating a new workload or finding the existing workload id")
    try:
        workloadId = FindWorkload(WACLIENT, WORKLOADNAME)
        logger.info("Found workload with id %s" % workloadId)
    except:
        CreateNewWorkload(WACLIENT, WORKLOADNAME, DESCRIPTION,
                          REVIEWOWNER, ENVIRONMENT, AWSREGIONS, LENSES)
        workloadId = FindWorkload(WACLIENT, WORKLOADNAME)
        logger.info("New workload created with id %s" % workloadId)

    listOfLenses = listLens(WACLIENT)
    logger.info("Lenses currently available: %s" % listOfLenses)
    workloadJson = GetWorkload(WACLIENT, workloadId)
    logger.info("Workload ID '%s' has lenses '%s'" %
                (workloadId, workloadJson['Lenses']))

    # STEP 3 - Performing a review
    # https://wellarchitectedlabs.com/well-architectedtool/200_labs/200_using_awscli_to_manage_wa_reviews/3_perform_review/
    logger.info("3 - Performing a review")
    lens = 'foundationaltechnicalreview'
    category = 'security'
    selectedChoices = []
    # Sec 1.
    questionId = findQuestionId(
        WACLIENT, workloadId, lens, category, 'How do you secure your AWS accounts?')
    if test_root_mfa():
        selectedChoices.append(findChoiceId(WACLIENT, workloadId,
                                            lens, questionId, 'Root user has multi-factor authentication (MFA) enabled.'))
    if test_root_access_keys():
        selectedChoices.append(findChoiceId(WACLIENT, workloadId,
                                            lens, questionId, 'Root user has no access keys'))
    if test_organization():
        selectedChoices.append(findChoiceId(WACLIENT, workloadId,
                                            lens, questionId, 'Use AWS Organizations to manage your accounts.'))
    if len(selectedChoices) > 0:
        updateAnswersForQuestion(
            WACLIENT, workloadId, lens, questionId, selectedChoices, 'Automatomation')

    # Sec 2.
    questionId = findQuestionId(
        WACLIENT, workloadId, lens, category, 'How do you configure identities for people and machines?')
    if test_user_mfa():
        selectedChoices.append(findChoiceId(WACLIENT, workloadId,
                                            lens, questionId, 'All IAM users have multi-factor authentication(MFA) enabled'))
    #if test_externalid_roles():
    #    selectedChoices.append(findChoiceId(WACLIENT, workloadId,
    #                                        lens, questionId, 'Use unique external ID for cross-account roles'))
    #if len(selectedChoices) > 0:
    #    updateAnswersForQuestion(
    #        WACLIENT, workloadId, lens, questionId, selectedChoices, 'Automatomation')

#
#    # STEP 4 - Saving a milestone
#    # https://wellarchitectedlabs.com/well-architectedtool/200_labs/200_using_awscli_to_manage_wa_reviews/4_save_milestone/
#    logger.info("4 - Saving a Milestone")
#
#    logger.info("4 - STEP1 - Create a Milestone")
#
#    milestones = listMilestones(WACLIENT, workloadId)
#    milestoneCount = jmespath.search("length([*].MilestoneNumber)", milestones)
#    logger.info("Workload %s has %s milestones" % (workloadId, milestoneCount))
#
#    milestoneNumber = createMilestone(WACLIENT, workloadId, 'Rev1')
#    logger.info("Created Milestone #%s called Rev1" % milestoneNumber)
#
#    logger.info("4 - STEP2 - List all Milestones")
#
#    milestones = listMilestones(WACLIENT, workloadId)
#    milestoneCount = jmespath.search("length([*].MilestoneNumber)", milestones)
#    logger.info("Now workload %s has %s milestones" %
#                (workloadId, milestoneCount))
#
#    logger.info("4 - STEP3 - Retrieve the results from a milestone")
#
#    riskCounts = getMilestoneRiskCounts(WACLIENT, workloadId, milestoneNumber)
#    logger.info("Risk counts for all lenses for milestone %s are: %s " %
#                (milestoneNumber, riskCounts))
#
#    logger.info(
#        "4 - STEP4 - List all question and answers based from a milestone")
#    answers = listAllAnswers(WACLIENT, workloadId,
#                             'wellarchitected', milestoneNumber)
#
#    # STEP 5 - Viewing and downloading the report
#    # https://wellarchitectedlabs.com/well-architectedtool/200_labs/200_using_awscli_to_manage_wa_reviews/5_view_report/
#    logger.info("5 - Viewing and downloading the report")
#    logger.info("5 - STEP1 - Gather pillar and risk data for a workload")
#
#    lensReview = getLensReview(WACLIENT, workloadId, 'wellarchitected')
#    logger.info("The Well-Architected base framework has the following RiskCounts %s " %
#                lensReview['RiskCounts'])
#
#    logger.info("5 - STEP2 - Generate and download workload PDF")
#    lensReviewBase64PDF = getLensReviewPDFReport(
#        WACLIENT, workloadId, 'wellarchitected')
#    # lensReviewPDF = base64.b64decode(lensReviewBase64PDF)
#    # We will write the PDF to a file in the same directory
#    with open("WAReviewOutput.pdf", "wb") as fh:
#        fh.write(base64.b64decode(lensReviewBase64PDF))
#
#    # STEP 6 - Teardown
#    # https://wellarchitectedlabs.com/well-architectedtool/200_labs/200_using_awscli_to_manage_wa_reviews/6_cleanup/
#    logger.info("6 - Teardown")
#
#    # Allow user to keep the workload
#    input("\n*** Press Enter to delete the workload or use ctrl-c to abort the script and keep the workload")
#
#    logger.info("6 - STEP1 - Delete Workload")
#    DeleteWorkload(WACLIENT, workloadId)
#


if __name__ == "__main__":
    main()
