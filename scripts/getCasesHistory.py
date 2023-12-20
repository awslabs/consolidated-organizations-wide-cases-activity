#!/usr/bin/env python

import boto3
import datetime
import botocore
import sys, getopt



sup = boto3.client('support')
org = boto3.client('organizations')
sts = boto3.client('sts')
ddb = boto3.resource('dynamodb')
comprehend = boto3.client('comprehend')
ddbTable = "COCA"
Sentiments = {"POSITIVE": 3, "NEUTRAL": 2, "MIXED": 1, "NEGATIVE": 0}

def get_accounts_list(org_client):
    po = org_client.get_paginator('list_accounts')
    pi = po.paginate().build_full_result()
    return [a['Id'] for a in pi['Accounts'] if a['Status'] == 'ACTIVE']

def get_support_cases_list(sup):
    ps = sup.get_paginator('describe_cases')
    # get cases created in the last 120 days
    date = datetime.datetime.now() - datetime.timedelta(days=120)
    try:
        pi = ps.paginate(
                includeResolvedCases=True,
                afterTime=date.strftime('%Y-%m-%d')
            ).build_full_result()
    # if account is not subscribed to premium supoprt, we get an exception
    except botocore.exceptions.ClientError as e:
        return False
    return pi['cases']

def get_credentials(account_id,role):
    role_arn = "arn:aws:iam::"+account_id+":role/"+role
    assumed_role = sts.assume_role(
            RoleArn = role_arn,
            RoleSessionName = "SupportKPIAssumeRole"
            )
    return assumed_role['Credentials']

def get_my_payer():
    return org.describe_organization()['Organization']['MasterAccountId']

def get_number_of_comms(comms):
    nbcomm_aws = 0
    nbcomm_cx = 0
    for c in comms['recentCommunications']['communications']:
        if c['submittedBy'] == "Amazon Web Services":
            nbcomm_aws += 1
        else:
            nbcomm_cx += 1
    return {'aws': nbcomm_aws, 'cx': nbcomm_cx}

def get_last_update_info(caseDict):
    # gets timestamp and source from last communication
    # returns timestamp and source as string
    return True

def get_sentiment_from_message(message, language):
    if len(str(message)) > 0 and len(str(message)) < 5000:
        r = comprehend.detect_sentiment(Text=str(message),LanguageCode=language)
        return r['Sentiment']
    else:
        return 'NEUTRAL'

def get_dominant_language(message):
    if len(str(message)) > 0:
        r = comprehend.detect_dominant_language(Text=str(message))
        return r['Languages'][0]['LanguageCode']
    else:
        return 'en'

def is_rto_met(caseDict):
    rto_times = {
            'low': 1440,
            'normal': 720,
            'high': 240,
            'urgent': 60,
            'critical': 15
    }
    rto = rto_times[caseDict['severityCode']]
    a = caseDict['timeCreated']
    b = caseDict['recentCommunications']['communications']
    for i in range(-1,-len(b),-1):
        if b[i]['submittedBy'] == "Amazon Web Services":
            da = datetime.datetime.strptime(a,'%Y-%m-%dT%H:%M:%S.%fZ')
            db = datetime.datetime.strptime(b[i]['timeCreated'],'%Y-%m-%dT%H:%M:%S.%fZ')
            diff = db - da
            if divmod(diff.total_seconds(),60)[0] > rto:
                return False
    return True

def get_last_cx_comm(caseDict):
    comms = caseDict['recentCommunications']['communications']
    for i in range(0,len(comms),1):
        if comms[i]['submittedBy'] != "Amazon Web Services":
            return comms[i]['body']
    return -1


def insert_case_in_ddb(caseDict,account):
    comms = get_number_of_comms(caseDict)
    rto = is_rto_met(caseDict)
    table = ddb.Table(ddbTable)
    message = get_last_cx_comm(caseDict)
    language = get_dominant_language(message)
    sentiment = get_sentiment_from_message(message, language)
    caseItem={
                'caseId': caseDict['caseId'],
                'awsAccount': account,
                'displayId': caseDict['displayId'],
                'subject': caseDict['subject'],
                'caseStatus': caseDict['status'],
                'serviceCode': caseDict['serviceCode'],
                'categoryCode': caseDict['categoryCode'],
                'severityCode': caseDict['severityCode'],
                'submittedBy': caseDict["recentCommunications"]["communications"][-1]["submittedBy"],
                'timeCreated': caseDict['timeCreated'],
                'timeLastUpdated': caseDict["recentCommunications"]["communications"][0]["timeCreated"],
                'lastUpdatedBy': caseDict["recentCommunications"]["communications"][0]["submittedBy"],
                'nbReopens': 0,
                'sentiment': Sentiments[sentiment],
                'sentimentTrend': -1,
                'nbAWSComms': comms['aws'],
                'nbCustomerComms': comms['cx'],
                'caseLanguage': '',
                'rtoMet': rto,
                }
    if caseDict['status'] == 'resolved':
        caseItem['timeLastResolved'] = caseDict["recentCommunications"]["communications"][0]["timeCreated"]
    table.put_item(Item=caseItem)


def usage():
    name = sys.argv[0]
    print(f"usage: {name} [-h] [-d n] [-p] [-r] [-o]")
    print("-h: this help")
    print("-d/--days n: import cases created in the last <n> days")
    print("-p/--payers: comma separated list of payers")
    print("-r/--assume-role: name of the role to assume in each account for DescribeCases calls (defaults to COCAAssumeRole)")
    print("-o/--account-map-role: name of the role to assume in the payer account(s) to describe the Organizations (defaults to COCAAccountMapRole)")
    sys.exit()

def main(argv):
    payers = []
    accounts = []
    role = "COCAAssumeRole"
    orole = "COCAAccountMapRole"
    days = 120
    opts, args = getopt.getopt(argv,"hp:d:r:", ["payers","days","assume-role"])
    for opt, arg in opts:
        if opt == "-h":
            usage()
        elif opt in ("-p", "--payers"):
            payers = arg.split(',')
        elif opt in ("-d", "--days"):
            days = arg
        elif opt in ("-r", "--assume-role"):
            role = arg
        elif opt in ("-o", "--account-map-role"):
            orole = arg
    payers.append(get_my_payer())
    print(f"Listing accounts in {len(payers)} AWS Organizations")
    for p in payers:
        creds = get_credentials(p, orole)
        org = boto3.client('organizations',
                    aws_access_key_id=creds['AccessKeyId'],
                    aws_secret_access_key=creds['SecretAccessKey'],
                    aws_session_token=creds['SessionToken']
        )
        accounts += get_accounts_list(org)
    print(f"We found {len(accounts)} accounts, proceeding to import cases")
    runningAccount = sts.get_caller_identity()['Account']

    print("Importing all support cases created in the last {} days, please be patient".format(days))
    for account in accounts:
        print("working with account {}".format(account))
        if account == runningAccount:
            sup = boto3.client('support')
        else:
            creds = get_credentials(account,role)
            sup = boto3.client('support',
                    aws_access_key_id=creds['AccessKeyId'],
                    aws_secret_access_key=creds['SecretAccessKey'],
                    aws_session_token=creds['SessionToken']
            )
        cases_list = get_support_cases_list(sup)
        if cases_list:
            print("-- importing {} cases for account {}".format(len(cases_list),account))
            for caseDict in cases_list:
                insert_case_in_ddb(caseDict,account)

        else:
            print('{} does not have any support cases, or no  premium support subscription'.format(account))



if __name__ == "__main__":
    main(sys.argv[1:])
