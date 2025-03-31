import boto3
import logging
from datetime import datetime
from typing import List, Dict, Any

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Create a formatter
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')

# Add handler if running locally (Lambda automatically adds a handler)
if not logger.handlers:
    handler = logging.StreamHandler()
    handler.setFormatter(formatter)
    logger.addHandler(handler)

def get_all_regions() -> List[str]:
    """Get a list of all enabled AWS regions."""
    ec2_client = boto3.client('ec2')
    regions = [
        region['RegionName']
        for region in ec2_client.describe_regions(
            Filters=[
                {
                    'Name': 'opt-in-status',
                    'Values': ['opt-in-not-required', 'opted-in']
                }
            ]
        )['Regions']
    ]
    logger.info(f"Found {len(regions)} enabled AWS regions")
    return regions

def get_asg_instance_ids(ec2_client) -> set:
    """Get set of instance IDs that are part of Auto Scaling Groups."""
    asg_client = boto3.client('autoscaling', region_name=ec2_client.meta.region_name)
    asg_instances = set()

    logger.info(f"Checking ASG instances in region {ec2_client.meta.region_name}")
    paginator = asg_client.get_paginator('describe_auto_scaling_instances')
    for page in paginator.paginate():
        for instance in page['AutoScalingInstances']:
            asg_instances.add(instance['InstanceId'])

    logger.info(f"Found {len(asg_instances)} EC2 instances in ASGs")
    return asg_instances

def get_non_asg_instances(region: str) -> List[Dict[str, Any]]:
    """Get instances not associated with ASG in a specific region."""
    ec2_client = boto3.client('ec2', region_name=region)
    logger.info(f"Checking for non-ASG instances in region {region}")

    # Get all instances that are running or stopped
    paginator = ec2_client.get_paginator('describe_instances')
    instances = []

    for page in paginator.paginate(
        Filters=[{
            'Name': 'instance-state-name',
            'Values': ['running', 'stopped']
        }]
    ):
        for reservation in page['Reservations']:
            instances.extend(reservation['Instances'])

    # Get instances in ASGs
    asg_instances = get_asg_instance_ids(ec2_client)

    # Filter out instances that are part of ASGs
    non_asg = [
        instance for instance in instances
        if instance['InstanceId'] not in asg_instances
    ]

    logger.info(f"Found {len(non_asg)} instances not in ASGs in region {region}")
    return non_asg

def check_compliance(event: Dict[str, Any]) -> str:
    """Check if there are any EC2 instances not in ASGs."""
    try:
        logger.info("Starting compliance check")
        for region in get_all_regions():
            non_asg_instances = get_non_asg_instances(region)
            if non_asg_instances:
                logger.warning(f"Found {len(non_asg_instances)} instances not in ASGs in {region}")
                return 'NON_COMPLIANT'
        logger.info("All instances are part of ASGs")
        return 'COMPLIANT'
    except Exception as e:
        logger.error(f"Error checking compliance: {str(e)}", exc_info=True)
        return 'NON_COMPLIANT'

def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """AWS Lambda handler function."""
    try:
        logger.info("Starting Lambda handler")
        config = boto3.client('config')
        compliance_type = check_compliance(event)

        evaluation = {
            'ComplianceResourceType': 'AWS::::Account',
            'ComplianceResourceId': event['accountId'],
            'ComplianceType': compliance_type,
            'OrderingTimestamp': datetime.now()
        }

        config.put_evaluations(
            Evaluations=[evaluation],
            ResultToken=event['resultToken']
        )

        logger.info(f"Completed evaluation with status: {compliance_type}")
        return {
            'statusCode': 200,
            'body': f'Evaluation complete. Compliance status: {compliance_type}'
        }

    except Exception as e:
        logger.error(f"Error evaluating compliance: {str(e)}", exc_info=True)
        raise
