## Deployment Guide

### Table of content:

* [Before you start](./DEPLOYMENT.md#before-you-start)

* [Amazon QuickSight pre requisites](./DEPLOYMENT.md#amazon-quicksight-pre-requisites)

* [Self hosting the CloudFormation stacks](./DEPLOYMENT.md#self-hosting-the-cloudformation-stacks)

* [Standard deployment](./DEPLOYMENT.md#standard-deployment)

* [Multi-Organizations deployment](./DEPLOYMENT.md#multi-organizations-deployment)

* [Importing cases history](./DEPLOYMENT.md#importing-cases-history)


### Before you start

* The solution's central dataset and dashboard reside in a linked account of your AWS Organizations (from now on referred to as Central Account).

* The solution can be deployed for one or multiple AWS Organizations. The above-mentioned Central Account exists in the Central Organizations, where you will use the dashboard. The other Organizations will from now on be referred to as Leaf Organizations.

* The solution can be deployed in any of the three regions where [AWS Support events are posted in the default eventBus](https://docs.aws.amazon.com/awssupport/latest/user/event-bridge-support.html): **us-east-1**, **us-west-2**, **eu-west-1**.

* The solution uses [AWS CloudFormation stacksets](https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/what-is-cfnstacksets.html). Enable Trusted Access to deploy CloudFormation stacksets across your AWS Organizations, which is documented in this [guide](https://docs.aws.amazon.com/organizations/latest/userguide/services-that-can-integrate-cloudformation.html). Grant self-managed permissions to your Payer and Central accounts as described in this [guide](https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/stacksets-prereqs-self-managed.html). When going for the multi-Organizations deployment, you only need to grant self-managed permissions in your Central Organizations.

* The solution requires an S3 bucket in the Central Account that will be used by Amazon Athena (from now on referred to as Athena Spillover bucket). It must be in the same region as the region you want to deploy the solution in.

* The solution requires an active Amazon QuickSight subscription in the Central account. If you do not have one, follow the [documentation](https://docs.aws.amazon.com/quicksight/latest/user/signing-up.html) to sign up for QuickSight. An Enterprise subscription is required.

### Amazon QuickSight pre requisites

All the actions listed below must be done in your Central Account.

#### Give Amazon QuickSight read and write access to you Athena Spillover bucket

1. Inside Amazon QuickSight, choose your profile name (upper right). Choose **Manage QuickSight**, and then choose **Security & permissions**.
2. Choose **Add or remove**.
3. Locate Amazon S3 in the list. If the checkbox is clear, select the checkbox next to Amazon S3. If the checkbox is selected, choose **Details**, and then choose **Select S3 buckets**.
4. Choose your Athena Spillover bucket and select both checkboxes, the one in the **S3 bucket** column, and the one in the **Write permission for Athena Workgroup** column.
5. Choose **Finish**.
6. Choose **Save**.

#### Create a group in Amazon QuickSight and add your user in the group

1. Inside Amazon QuickSight, choose your profile name (upper right). Choose **Manage QuickSight**, and then choose **Manage groups**.
2. Choose **New group**, and use **COCAAdmin** as name.
3. Choose **Create**.
4. Choose the **COCAAdmin** group.
5. Choose **Add user**.
6. Search your user and choose **Add**.
7. Repeat for any user you want to allow. If you can't find the user, make sure they have accessed Amazon QuickSight.

#### Provision additional SPICE capacity

Verify if you have enough free SPICE Capacity in the region you want to deploy in, or purchase extra capacity.

1. Inside Amazon QuickSight, choose your profile name (upper right), make sure you are in the region where you wan to deploy the solution. Choose **Manage QuickSight**, and then choose **SPICE capacity**.
2. Verify you have at least 10GB of free capacity. If you do, skip to the next pre requisite.
3. If you don't, Select **Purchase more capacity**.
4. Set 10GB and choose **Purchase SPICE capacity**.

#### Allow Amazon QuickSight to invoke a Lambda function.

1. Open the Amazon IAM console and search the role you use for the Amazon QuickSight service. By default, it is **aws-quicksight-service-role-v0**. If you configured a different one, open it.
2. Choose **Add permissions** then **Create inline policy**.
3. Choose the **JSON** policy editor.
4. Add a policy such as the one below. Make sure you substitute `${accountid}` with the AWS Account ID of your Central Account. `${AthenaCatalogName}` must be substituted with the value that you will set for the CloudFormation stack parameter of the same name. It defaults to `ddbdata` in the stack.

```
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Sid": "VisualEditor0",
            "Effect": "Allow",
            "Action": "lambda:InvokeFunction",
            "Resource": "arn:aws:lambda:${region}:${accountid}:function:${AthenaCatalogName}"
        }
    ]
}
```
5. Choose **Next**.
6. Give the inline policy a name, and choose **Create policy**.


### Self hosting the CloudFormation stacks

1. Create or reuse an existing S3 bucket. From now on we will refer to this bucket as **yourbucket**.
2. Create a bucket policy that allows your payer account(s) and the central account to retrieve the stacks. See example below, replace the AWS Account IDs with your account IDs, and `yourbucket` with the name of the bucket where you self host the CloudFormation stacks.

```
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Principal": {
                "AWS": [
                    "arn:aws:iam::111111111111:root",
                    "arn:aws:iam::222222222222:root",
                    "arn:aws:iam::333333333333:root"
                ]
            },
            "Action": [
                "s3:GetObject",
                "s3:List*"
            ],
            "Resource": [
                "arn:aws:s3:::yourbucket/*",
                "arn:aws:s3:::yourbucket"
            ]
        }
    ]
}

```
3. Clone this repository
4. Navigate in the directory where you cloned the repository, and then in the `cloudformation/` sub directory.
5. Upload the content of this sub directory at the root of yourbucket.

### Standard deployment

1. Open the [AWS Organizations console](https://us-east-1.console.aws.amazon.com/organizations/v2/home) in your payer account. Take note of the **Organizations ID** (o-xxxxxxxxxx) and the **Root ID** (r-yyyy). These will be used as parameters for the CloudFormation stack.
2. Open the [AWS CloudFormation console](https://us-east-1.console.aws.amazon.com/cloudformation/home) in the region you intend to deploy the solution in (as a reminder, it has to be one of **us-east-1**, **us-west-2** or **eu-west-1**).
3. Choose **Create stack**, then **With new resources (standard)**.
4. Choose **Template is ready**, **Amazon S3 URL**, and input the Amazon S3 URL of the self hosted COCAstack.yml in **yourbucket**, eg: https://yourbucket.s3.amazonaws.com/COCAstack.yml.
5. Choose **Next**.
6. Give the stack a name.
7. Leave all parameters to their default value, unless did not substitute  **AthenaCatalogName** with **ddbdata** in the QuickSight pre requisites about allowing QuickSight to invoke a Lambda function. If that's the case, set **AthenaCatalogName** value to the same.
8. Set **AthenaSpilloverBucket** value to the name of your Athena Spillover bucket that you created in the Deployment guide pre requisites.
9. Set **CentralAccountId** value to the AWS Account ID of your Central Account.
10. Set **AWSOrgId** value to the ID of your AWS Organizations (noted in step #1).
11. Set **COCACollectionStackSetDeployTargetsOU** value to the ID of your Root OU (noted in step #1).
12. Set **COCABucket** value to the name of the bucket where you self host the stacks (eg: yourbucket).
13. If you signed up for Amazon QuickSight in a region that is not **us-east-1**, **COCAQuicksightRegion** to the region you signed up for Amazon QuickSight in.
14. Choose **Next**.
15. Add optional tags if you want. Leave **Permissions**, **Stack failure options**, and **Advanced options** as is.
16. Choose **Next**.
17. Review your stack options and parameters. Under **Capabilities**, select the checkbox, and then choose **Submit**.

When the stack is done deploying, open the AWS Console for your Central Account. Open Amazon QuickSight, navigate to Dashboards, and you will see COCADashboard. To import your cases history, see [Importing cases history](./DEPLOYMENT.md#importing-cases-history) below.


### Multi-Organizations deployment

In this deployment, start with each Leaf Organizations, then do the Central Organizations.

The region you deploy in must be the same for all Organizations.

#### In each Leaf Organizations

1. Open the [AWS Organizations console](https://us-east-1.console.aws.amazon.com/organizations/v2/home) in your payer account. Take note of the **Organizations ID** (o-xxxxxxxxxx) and the **Root ID** (r-yyyy). These will be used as parameters for the CloudFormation stack.
2. Open the [AWS CloudFormation console](https://us-east-1.console.aws.amazon.com/cloudformation/home) in the region you intend to deploy the solution in (as a reminder, it has to be one of **us-east-1**, **us-west-2** or **eu-west-1**).
3. Choose **Create stack**, then **With new resources (standard)**.
4. Choose **Template is ready**, **Amazon S3 URL**, and input the Amazon S3 URL of the self hosted COCAstack_leaf.yml in **yourbucket**, eg: https://yourbucket.s3.amazonaws.com/COCAstack_leaf.yml.
5. Choose **Next**.
6. Give the stack a name.
7. Set **CentralAccountId** value to the AWS Account ID of your Central Account.
8. Set **COCACollectionStackSetDeployTargetsOU** value to the ID of your Root OU (noted in step #1).
9. Set **COCABucket** value to the name of the bucket where you self host the stacks (eg: yourbucket).
10. Choose **Next**.
11. Add optional tags if you want. Leave **Permissions**, **Stack failure options**, and **Advanced options** as is.
12. Choose **Next**.
13. Review your stack options and parameters. Under **Capabilities**, select the checkbox, and then choose **Submit**.

For each Leaf Organizations, take note of the **Organizations ID** and the **Payer Account ID**. They will be parameters for the CloudFormation stack in the Central Organizations.

#### In the Central Organizations

Only proceed with this step when the deployment is done in all your AWS Organizations, as there is a Lambda backed CustomResource that will try to use a role in every Leaf Organizations' payer account during deployment. It will fail if the role does not exist.

1. Open the [AWS Organizations console](https://us-east-1.console.aws.amazon.com/organizations/v2/home) in your payer account. Take note of the **Organizations ID** (o-xxxxxxxxxx) and the **Root ID** (r-yyyy). These will be used as parameters for the CloudFormation stack.
2. Open the [AWS CloudFormation console](https://us-east-1.console.aws.amazon.com/cloudformation/home) in the region you intend to deploy the solution in (as a reminder, it has to be one of **us-east-1**, **us-west-2** or **eu-west-1**).
3. Choose **Create stack**, then **With new resources (standard)**.
4. Choose **Template is ready**, **Amazon S3 URL**, and input the Amazon S3 URL of the self hosted COCAstack.yml in **yourbucket**, eg: https://yourbucket.s3.amazonaws.com/COCAstack.yml.
5. Choose **Next**.
6. Give the stack a name.
7. Leave all parameters to their default value, unless did not substitute  **AthenaCatalogName** with **ddbdata** in the QuickSight pre requisites about allowing QuickSight to invoke a Lambda function. If that's the case, set **AthenaCatalogName** value to the same.
8. Set **AthenaSpilloverBucket** value to the name of your Athena Spillover bucket that you created in the Deployment guide pre requisites.
9. Set **CentralAccountId** value to the AWS Account ID of your Central Account.
10. Set **AWSOrgId** value to the IDs of all your AWS Organizations (Central and Leafs), as a comma separated string, eg: o-yyyyyyy,o-xxxxxxxx,o-zzzzzzzz
11. Set **COCACollectionStackSetDeployTargetsOU** value to the ID of your Root OU (noted in step #1).
12. Set **COCABucket** value to the name of the bucket where you self host the stacks (eg: yourbucket).
13. Set **COCAPayers** value to the Payer Account IDs of your Leaf AWS Organizations, as a comma separated string, eg: 111111111111,222222222222,333333333333
14. If you signed up for Amazon QuickSight in a region that is not **us-east-1**, **COCAQuicksightRegion** to the region you signed up for Amazon QuickSight in.
15. Choose **Next**.
16. Add optional tags if you want. Leave **Permissions**, **Stack failure options**, and **Advanced options** as is.
17. Choose **Next**.
18. Review your stack options and parameters. Under **Capabilities**, select the checkbox, and then choose **Submit**.

When the stack is done deploying, open the AWS Console for your Central Account. Open Amazon QuickSight, navigate to Dashboards, and you will see COCADashboard. To import your cases history, see [Importing cases history](./DEPLOYMENT.md#importing-cases-history) below.

### Importing cases history

For this step you will need valid CLI credentials for your Central Account. The easiest way is to use [AWS CloudShell](https://us-east-1.console.aws.amazon.com/cloudshell/home).

1. Clone a copy of this repository.
2. Navigate into the directory where you cloned the repository, and then the `scripts/` sub directory.
3. Execute the script as described below, depending on which deployment you opted for.

```
❯ python getCasesHistory.py -h
usage: getCasesHistory.py [-h] [-d n] [-p] [-r] [-o]
-h: this help
-d/--days n: import cases created in the last <n> days
-p/--payers: comma separated list of payers
-r/--assume-role: name of the role to assume in each account for DescribeCases calls (defaults to COCAAssumeRole)
-o/--account-map-role: name of the role to assume in the payer account(s) to describe the Organizations (defaults to COCAAccountMapRole)
```

For a standard deployment, the following will import cases created in the last 120 days.
```
❯ python getCasesHistory.py
```
Use `-d` to control the lookback period.
```
❯ python getCasesHistory.py -d 360
```

For a multi-Organizations deployment, you have to give the list of payer accounts for each Leaf Organizations.
```
❯ python getCasesHistory.py -d 360 -p "111111111111,222222222222,333333333333"
```

4. Once the script is done executing, open Amazon QuickSight in your Central Account. Navigate to Datasets, choose **COCAQuicksightDataset**.
5. Open the **Refresh** tab, and choose **Refresh now**.

When the dataset is done refreshing, open the dashboard.
