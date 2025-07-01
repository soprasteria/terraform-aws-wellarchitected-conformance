"""
Well-Architected Report Generator Lambda Function

This Lambda function generates an HTML report from AWS Config Conformance Packs
compliance data and uploads it to a dedicated S3 bucket.

Environment Variables:
    LOG_LEVEL: Logging level (default: INFO)
    SECURITY_CONFORMANCE_PACK: Name of the Security conformance pack
    RELIABILITY_CONFORMANCE_PACK: Name of the Reliability conformance pack
    COST_OPTIMIZATION_CONFORMANCE_PACK: Name of the Cost Optimization conformance pack
    S3_BUCKET_NAME: Name of the dedicated S3 bucket to store HTML reports
    TIMEZONE: Timezone for date/time formatting (default: Europe/Paris)

Event Parameters:
    workload_id: ID of the Well-Architected Tool workload (used for consistency with wa_tool_updater)
    dry_run: Whether to run in dry-run mode (no actual uploads)
    clean_notes: Ignored in this function (included for compatibility with wa_tool_updater)
"""

import boto3
import json
import logging
import os
import pytz
import re
from datetime import datetime
from botocore.exceptions import ClientError
from jinja2 import Environment, FileSystemLoader, select_autoescape

# Configure logging
logger = logging.getLogger()
log_level = os.environ.get('LOG_LEVEL', 'INFO')
logger.setLevel(getattr(logging, log_level))

# Initialize clients
config_client = boto3.client('config')
sts_client = boto3.client('sts')
wellarchitected_client = boto3.client('wellarchitected')

# Configure timezone
DEFAULT_TIMEZONE = 'Europe/Paris'  # Central European Time (Paris)
timezone_name = os.environ.get('TIMEZONE', DEFAULT_TIMEZONE)
try:
    timezone = pytz.timezone(timezone_name)
    logger.info(f"Using timezone: {timezone_name}")
except pytz.exceptions.UnknownTimeZoneError:
    logger.warning(f"Unknown timezone: {timezone_name}. Falling back to {DEFAULT_TIMEZONE}")
    timezone = pytz.timezone(DEFAULT_TIMEZONE)

# Get conformance pack names from environment variables
SECURITY_CONFORMANCE_PACK = os.environ.get('SECURITY_CONFORMANCE_PACK', 'Well-Architected-Security')
RELIABILITY_CONFORMANCE_PACK = os.environ.get('RELIABILITY_CONFORMANCE_PACK', 'Well-Architected-Reliability')
COST_OPTIMIZATION_CONFORMANCE_PACK = os.environ.get('COST_OPTIMIZATION_CONFORMANCE_PACK', 'Well-Architected-Cost-Optimization')
S3_BUCKET_NAME = os.environ.get('S3_BUCKET_NAME', '')

# Mapping of conformance pack names to Well-Architected pillars
PILLAR_MAPPING = {
    SECURITY_CONFORMANCE_PACK: 'security',
    RELIABILITY_CONFORMANCE_PACK: 'reliability',
    COST_OPTIMIZATION_CONFORMANCE_PACK: 'costOptimization'
}

def get_conformance_pack_details(conformance_pack_name):
    """
    Get details of a conformance pack including its rules.
    Manually handles pagination for result sets larger than 100.
    """
    try:
        rules_list = []
        next_token = None

        while True:
            # Prepare kwargs for the API call
            kwargs = {
                'ConformancePackName': conformance_pack_name,
                'Limit': 100
            }

            # Add NextToken if we have one
            if next_token:
                kwargs['NextToken'] = next_token

            # Make the API call
            response = config_client.describe_conformance_pack_compliance(**kwargs)

            # Add the rules from this page
            rules_list.extend(response.get('ConformancePackRuleComplianceList', []))

            # Get the next token
            next_token = response.get('NextToken')

            # If no next token, we've reached the end
            if not next_token:
                break

        return rules_list

    except Exception as e:
        logger.error(f"Error getting conformance pack details: {e}")
        return []

def get_rule_details(rule_name):
    """Get details of a config rule including non-compliant resources."""
    try:
        response = config_client.get_compliance_details_by_config_rule(
            ConfigRuleName=rule_name,
            ComplianceTypes=['NON_COMPLIANT', 'COMPLIANT'],
            Limit=100
        )
        return response.get('EvaluationResults', [])
    except Exception as e:
        logger.error(f"Error getting rule details: {e}")
        return []

def extract_question_id(rule_name):
    """
    Extract QuestionId from an AWS Config rule name.

    Format: QuestionNumber-ActualQuestionId_bp_name-of-check
    Examples:
    - SEC05-network-protection_bp_vpc-default-security-group-closed-conformance-pack-qk5aog3dr
    - cost01-cloud-financial-management_bp_aws-budgets-conformance-pack-zg7bakjef
    - REL09-backing-up-data_bp_backup-plan-min-frequency-and-min-retention-check-conformance-pack-qyaut3rcc

    Args:
        rule_name: The AWS Config rule name

    Returns:
        Tuple of (question_number, actual_question_id) or (question_number, None) if actual_question_id not found
    """
    try:
        # First extract the question number (e.g., SEC05, REL09, cost01)
        # Handle both uppercase and lowercase prefixes
        number_pattern = r'([A-Za-z]{3,4}\d{2})'
        number_match = re.search(number_pattern, rule_name, re.IGNORECASE)

        if not number_match:
            logger.info(f"No question number found for rule_name={rule_name}")
            return None, None

        question_number = number_match.group(1).upper()  # Convert to uppercase for consistency

        # Then extract the actual questionId (e.g., network-protection, backing-up-data)
        # First try with the uppercase version
        id_pattern = f"{question_number}-([a-z0-9-]+)(?:_bp|_)"
        id_match = re.search(id_pattern, rule_name)

        if not id_match:
            # If that doesn't work, try with the lowercase version
            lowercase_question = question_number.lower()
            id_pattern = f"{lowercase_question}-([a-z0-9-]+)(?:_bp|_)"
            id_match = re.search(id_pattern, rule_name)

        if id_match:
            actual_question_id = id_match.group(1)
            logger.debug(f"Extracted question_number={question_number}, actual_question_id={actual_question_id} from rule_name={rule_name}")
            return question_number, actual_question_id

        # If we couldn't extract the actual questionId, just return the question number
        logger.info(f"Extracted question_number={question_number}, but couldn't extract actual_question_id from rule_name={rule_name}")
        return question_number, None

    except Exception as e:
        logger.warning(f"Error extracting QuestionId from rule name {rule_name}: {e}")
        return None, None

def get_question_details(workload_id, pillar_id, question_id):
    """
    Get question details from the Well-Architected Tool API for a specific question ID.

    Args:
        workload_id: The Well-Architected workload ID
        question_id: The question ID to look up

    Returns:
        Dictionary with question title and helpful resources, or None if not found
    """
    lens_alias = "wellarchitected"
    try:
        # Get lens ARN
        lens_response = wellarchitected_client.get_lens(
            LensAlias=lens_alias
        )
        #logger.info(f"lens_response={lens_response}")
        lens_arn = lens_response.get('Lens', {}).get('LensArn')

        # Get question details
        question_response = wellarchitected_client.get_answer(
            WorkloadId=workload_id,
            LensAlias=lens_alias,
            QuestionId=question_id
        )
        question_title = question_response.get('Answer', {}).get('QuestionTitle', '')
        helpful_resources = []
        choices = {}
        description = question_response.get('Answer', {}).get('QuestionDescription', '')

        # Extract helpful resources
        for resource in question_response.get('Answer', {}).get('HelpfulResources', []):
            helpful_resources.append({
                'title': resource.get('DisplayText', ''),
                'url': resource.get('Url', '')
            })

        # Extract choices and get Trusted Advisor checks for each choice
        for choice in question_response.get('Answer', {}).get('Choices', []):
            choice_id = choice.get('ChoiceId')
            choice_title = choice.get('Title')

            logger.debug(f"get_question_details choice_id={choice_id}, choice_title={choice_title}, lens_arn={lens_arn}")
            if choice_id and choice_title != "None of these" and pillar_id and lens_arn:
                # Get Trusted Advisor checks for this choice
                ta_checks = get_trusted_advisor_checks(workload_id, lens_arn, pillar_id, question_id, choice_id)

                choices[choice_id] = {
                    'title': choice_title,
                    'description': choice.get('Description', ''),
                    'resources': [],  # Will store compliance resources for this choice
                    'trusted_advisor_checks': ta_checks
                }

        return {
            'title': question_title,
            'description': description,
            'helpful_resources': helpful_resources,
            'choices': choices,
            'full_id': question_id,
            'pillar_id': pillar_id,
            'lens_arn': lens_arn
        }

    except Exception as e:
        logger.warning(f"Could not retrieve details for question {question_id}: {e}")
        return None

def get_question_titles_and_choices_fallback(workload_id):
    """
    Fallback method to get question titles and choices using workload-specific API calls.
    Used if export-lens fails.

    Args:
        workload_id: The Well-Architected workload ID

    Returns:
        Dictionary mapping ordered question IDs (e.g., SEC01) to their titles, choices, and helpful resources
    """
    question_data = {}
    lens_alias = "wellarchitected"  # Focus only on wellarchitected lens

    try:
        # Get all pillars and their questions
        pillars = {
            'security': 'SEC',
            'reliability': 'REL',
            'costOptimization': 'COST'
        }

        for pillar_id, prefix in pillars.items():
            try:
                # Use ListLensReviewImprovements without pagination
                response = wellarchitected_client.list_lens_review_improvements(
                    WorkloadId=workload_id,
                    LensAlias=lens_alias,
                    PillarId=pillar_id
                )

                # Collect all questions for this pillar
                questions = []
                for improvement in response.get('ImprovementSummaries', []):
                    question_id = improvement.get('QuestionId')
                    if question_id:
                        questions.append(question_id)

                # Process each question in order
                question_idx = 1
                for question_id in questions:
                    try:
                        # Get question details
                        question_response = wellarchitected_client.get_answer(
                            WorkloadId=workload_id,
                            LensAlias=lens_alias,
                            QuestionId=question_id
                        )

                        question_title = question_response.get('Answer', {}).get('QuestionTitle', '')
                        helpful_resources = []
                        choices = {}

                        # Extract helpful resources
                        for resource in question_response.get('Answer', {}).get('HelpfulResources', []):
                            helpful_resources.append({
                                'title': resource.get('DisplayText', ''),
                                'url': resource.get('Url', '')
                            })

                        # Extract choices
                        for choice in question_response.get('Answer', {}).get('Choices', []):
                            choice_id = choice.get('ChoiceId')
                            choice_title = choice.get('Title')
                            if choice_id and choice_title:
                                # Log the choice ID for debugging
                                logger.debug(f"Found choice: {choice_id} for question {question_id}")
                                choices[choice_id] = {
                                    'title': choice_title,
                                    'description': choice.get('Description', ''),
                                    'resources': []  # Will store compliance resources for this choice
                                }

                        # Create the ordered ID (e.g., SEC01, REL02)
                        ordered_id = f"{prefix}{question_idx:02d}"
                        question_idx += 1

                        # Extract the actual question ID part from the full ID
                        # Example: security_01 -> extract "01"
                        # Example: reliability_resiliency -> extract "resiliency"
                        actual_id_parts = question_id.split('_')
                        actual_question_id = actual_id_parts[-1] if len(actual_id_parts) > 1 else ""

                        question_data[ordered_id] = {
                            'title': question_title,
                            'helpful_resources': helpful_resources,
                            'choices': choices,
                            'full_id': question_id,  # Store the original ID for reference
                            'actual_id': actual_question_id  # Store the extracted actual ID part
                        }
                        logger.debug(f"Mapped ordered ID {ordered_id} to question {question_id} with actual_id {actual_question_id}")

                    except Exception as e:
                        logger.warning(f"Could not retrieve details for question {question_id}: {e}")

                logger.info(f"Mapped {question_idx-1} questions for pillar {pillar_id}")

            except Exception as e:
                logger.error(f"Error getting question data for pillar {pillar_id}: {e}")

    except Exception as e:
        logger.error(f"Error getting lens details: {e}")

    return question_data

def map_best_practice_to_question(best_practice_id):
    """
    Map a best practice ID (e.g., SEC01) to a Well-Architected question ID.
    This is a direct mapping since we're using the same ordered IDs.

    Args:
        best_practice_id: The best practice ID (e.g., SEC01)

    Returns:
        The same ID, since we're using ordered IDs as keys in our question_data dictionary
    """
    return best_practice_id

def collect_compliance_data(conformance_packs, workload_id=None):
    """
    Collect compliance data from all conformance packs for HTML report generation.
    Uses AWS Config checks as the reference and looks up question details from the Well-Architected Tool.

    Args:
        conformance_packs: List of conformance pack names to process
        workload_id: Well-Architected workload ID to retrieve question details

    Returns:
        Dictionary with compliance data organized by pillar and question
    """
    compliance_data = {}

    # Initialize pillar data
    for pillar_name in ['Security', 'Reliability', 'Cost Optimization']:
        compliance_data[pillar_name] = {}

    # Process each conformance pack
    for conformance_pack_name in conformance_packs:
        # Extract pillar name for this conformance pack
        pillar_name = None
        for prefix, pillar_id in PILLAR_MAPPING.items():
            if prefix in conformance_pack_name:
                if pillar_id == 'security':
                    pillar_name = 'Security'
                elif pillar_id == 'reliability':
                    pillar_name = 'Reliability'
                elif pillar_id == 'costOptimization':
                    pillar_name = 'Cost Optimization'
                break

        if not pillar_name:
            logger.warning(f"Could not determine pillar name for conformance pack: {conformance_pack_name}")
            continue

        # Get conformance pack rules
        rules = get_conformance_pack_details(conformance_pack_name)

        # Process each rule
        for rule in rules:
            rule_name = rule.get('ConfigRuleName')

            # Extract question number and actual question ID from rule name
            question_number, actual_question_id = extract_question_id(rule_name)

            if not question_number:
                logger.warning(f"Could not extract question number from rule name: {rule_name}")
                continue

            # Use question_number as the key in our data structure
            if question_number not in compliance_data[pillar_name]:
                # Initialize with basic information
                compliance_data[pillar_name][question_number] = {
                    'title': f"Best Practice {question_number}",
                    'description': '',
                    'helpful_resources': [],
                    'resources': [],
                    'config_rules': {},
                    'actual_question_id': actual_question_id
                }

                # If we have a workload_id and actual_question_id, try to get question details
                if workload_id and actual_question_id:
                    # Try to get question details from the Well-Architected Tool
                    question_details = get_question_details(workload_id, pillar_id, actual_question_id)
                    logger.debug(f"Got question details from the Well-Architected Tool API: {question_details}")
                    if question_details:
                        compliance_data[pillar_name][question_number]['title'] = question_details.get('title', compliance_data[pillar_name][question_number]['title'])
                        compliance_data[pillar_name][question_number]['description'] = question_details.get('description', '')
                        compliance_data[pillar_name][question_number]['helpful_resources'] = question_details.get('helpful_resources', [])
                        compliance_data[pillar_name][question_number]['full_id'] = actual_question_id
                        compliance_data[pillar_name][question_number]['choices'] = question_details.get('choices', {})

            # Get rule details including resources
            evaluation_results = get_rule_details(rule_name)

            for result in evaluation_results:
                resource_type = result.get('EvaluationResultIdentifier', {}).get('EvaluationResultQualifier', {}).get('ResourceType')
                resource_id = result.get('EvaluationResultIdentifier', {}).get('EvaluationResultQualifier', {}).get('ResourceId')
                resource_compliance = result.get('ComplianceType')

                resource_data = {
                    'resource_type': resource_type,
                    'resource_id': resource_id,
                    'compliance_status': resource_compliance,
                    'rule_name': rule_name,
                    'actual_question_id': actual_question_id
                }

                # Try to get the Name tag for this resource
                name_tag = get_resource_tags(resource_type, resource_id)
                resource_data['name_tag'] = name_tag if name_tag else "No tag"

                # Add resource to the main resources list
                compliance_data[pillar_name][question_number]['resources'].append(resource_data)

                # Track this config rule
                if rule_name not in compliance_data[pillar_name][question_number]['config_rules']:
                    compliance_data[pillar_name][question_number]['config_rules'][rule_name] = []

                compliance_data[pillar_name][question_number]['config_rules'][rule_name].append(resource_data)

    return compliance_data

def generate_html_report(compliance_data, account_id, region):
    """
    Generate HTML report from compliance data using Jinja2 templating

    Args:
        compliance_data: Dictionary containing compliance data by pillar and best practice
        account_id: AWS Account ID
        region: AWS Region

    Returns:
        HTML content as string
    """
    # Check if AWS Business or Enterprise Support is enabled
    business_support_enabled, support_message = check_business_support_enabled()

    # Setup Jinja2 environment
    template_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'templates')
    env = Environment(
        loader=FileSystemLoader(template_dir),
        autoescape=select_autoescape(['html', 'xml'])
    )

    # Get the template
    template = env.get_template('report_template.html')

    # Render the template with our data
    html_content = template.render(
        compliance_data=compliance_data,
        account_id=account_id,
        region=region,
        generation_time=datetime.now(timezone).strftime("%Y-%m-%d %H:%M:%S %Z"),
        business_support_enabled=business_support_enabled,
        support_message=support_message
    )

    return html_content

def upload_report_to_s3(html_content, bucket_name, dry_run=False):
    """
    Upload HTML report to S3 bucket

    Args:
        html_content: HTML content to upload
        bucket_name: S3 bucket name
        dry_run: Whether to run in dry-run mode (no actual uploads)

    Returns:
        S3 URL of the uploaded report
    """
    if dry_run:
        logger.info(f"DRY RUN: Would upload HTML report to S3 bucket {bucket_name}")
        return "s3://dry-run-no-upload"

    if not bucket_name:
        logger.warning("No S3 bucket name provided, skipping report upload")
        return ""

    s3_client = boto3.client('s3')

    # Generate filename with timestamp
    timestamp = datetime.now(timezone).strftime("%Y%m%d-%H%M%S")
    filename = f"Reports/well_architected_compliance_report_{timestamp}.html"

    try:
        s3_client.put_object(
            Bucket=bucket_name,
            Key=filename,
            Body=html_content,
            ContentType='text/html'
        )
        logger.info(f"Successfully uploaded report to s3://{bucket_name}/{filename}")
        return f"s3://{bucket_name}/{filename}"
    except Exception as e:
        logger.error(f"Error uploading report to S3: {str(e)}")
        return ""

def get_trusted_advisor_checks(workload_id, lens_arn, pillar_id, question_id, choice_id):
    """
    Get Trusted Advisor check details and compliance status for a specific pillar and choice.

    Args:
        workload_id: The Well-Architected workload ID
        lens_arn: The ARN of the lens
        pillar_id: The ID of the pillar
        question_id: The ID of the question
        choice_id: The ID of the choice

    Returns:
        List of Trusted Advisor check details with compliance status
    """

    try:
        # Get Trusted Advisor check details
        details_response = wellarchitected_client.list_check_details(
            WorkloadId=workload_id,
            LensArn=lens_arn,
            PillarId=pillar_id,
            QuestionId=question_id,
            ChoiceId=choice_id
        )

        # Get check summaries for compliance status
        try:
            summaries_response = wellarchitected_client.list_check_summaries(
                WorkloadId=workload_id,
                LensArn=lens_arn,
                PillarId=pillar_id,
                QuestionId=question_id,
                ChoiceId=choice_id
            )

            # Create a mapping of check IDs to their compliance status
            compliance_status = {}
            for summary in summaries_response.get('CheckSummaries', []):
                check_id = summary.get('CheckId')
                if check_id:
                    compliance_status[check_id] = {
                        'status': summary.get('Status'),
                        'risk': summary.get('Risk'),
                        'reason': summary.get('Reason', ''),
                        'flagged_resources': summary.get('FlaggedResources', 0),
                        'updated_at': summary.get('UpdatedAt', '')
                    }
            logger.debug(f"Got compliance status for {len(compliance_status)} checks")
        except Exception as e:
            logger.warning(f"Could not retrieve check summaries: {e}")
            compliance_status = {}

        check_details = []
        for check in details_response.get('CheckDetails', []):
            check_id = check.get('Id')
            status_info = compliance_status.get(check_id, {})

            check_details.append({
                'id': check_id,
                'name': check.get('Name', ''),
                'description': check.get('Description', ''),
                'provider': check.get('Provider', ''),
                'provider_name': check.get('ProviderName', ''),
                'status': status_info.get('status', 'UNKNOWN'),
                'risk': status_info.get('risk', 'UNKNOWN'),
                'reason': status_info.get('reason', ''),
                'flagged_resources': status_info.get('flagged_resources', 0),
                'updated_at': status_info.get('updated_at', '')
            })

        logger.debug(f"get_trusted_advisor_checks returned: {check_details}")
        return check_details

    except Exception as e:
        logger.warning(f"Could not retrieve Trusted Advisor check details for pillar {pillar_id}, question_id {question_id}, choice {choice_id}: {e}")
        return []

def lambda_handler(event, context):
    """
    Lambda function handler that generates an HTML report from AWS Config compliance data
    and uploads it to an S3 bucket.

    Args:
        event: Lambda event object containing parameters
        context: Lambda context object

    Returns:
        Dictionary with status and message
    """
    logger.info("Starting Well-Architected Report Generator")

    # Get parameters from the event
    workload_id = event.get('workload_id')
    dry_run = event.get('dry_run', True)

    # Validate S3 bucket name
    if not S3_BUCKET_NAME:
        error_msg = "No S3_BUCKET_NAME provided in environment variables"
        logger.error(error_msg)
        return {
            'statusCode': 400,
            'body': json.dumps({
                'status': 'error',
                'message': error_msg
            })
        }

    # Process each conformance pack
    conformance_packs = []
    if SECURITY_CONFORMANCE_PACK:
        conformance_packs.append(SECURITY_CONFORMANCE_PACK)
    if RELIABILITY_CONFORMANCE_PACK:
        conformance_packs.append(RELIABILITY_CONFORMANCE_PACK)
    if COST_OPTIMIZATION_CONFORMANCE_PACK:
        conformance_packs.append(COST_OPTIMIZATION_CONFORMANCE_PACK)

    if not conformance_packs:
        error_msg = "No conformance packs specified in environment variables"
        logger.error(error_msg)
        return {
            'statusCode': 400,
            'body': json.dumps({
                'status': 'error',
                'message': error_msg
            })
        }

    try:
        # Get AWS account ID and region
        account_id = sts_client.get_caller_identity()['Account']
        region = boto3.session.Session().region_name

        # Collect compliance data with question details if workload_id is provided
        logger.info("Collecting compliance data from AWS Config")
        compliance_data = collect_compliance_data(conformance_packs, workload_id)

        # Generate HTML report
        logger.info("Generating HTML report")
        html_content = generate_html_report(compliance_data, account_id, region)

        # Upload to S3
        logger.info(f"Uploading report to S3 bucket: {S3_BUCKET_NAME}")
        report_url = upload_report_to_s3(html_content, S3_BUCKET_NAME, dry_run)

        logger.info("Well-Architected Report Generator completed successfully")
        return {
            'statusCode': 200,
            'body': json.dumps({
                'status': 'success',
                'message': 'Well-Architected report generated successfully',
                'dry_run': dry_run,
                'report_url': report_url
            })
        }
    except Exception as e:
        error_msg = f"Error generating report: {str(e)}"
        logger.error(error_msg)
        return {
            'statusCode': 500,
            'body': json.dumps({
                'status': 'error',
                'message': error_msg
            })
        }
def check_business_support_enabled():
    """
    Check if AWS Business or Enterprise Support is enabled by attempting to call
    the AWS Support API. If we get a SubscriptionRequiredException, it means
    Business or Enterprise Support is not enrolled.

    Returns:
        Tuple of (is_enabled, message)
    """
    try:
        # Initialize AWS Support client
        support_client = boto3.client('support')

        # Try to call describe-trusted-advisor-checks
        response = support_client.describe_trusted_advisor_checks(language='en')

        # If we get here, Business or Enterprise Support is enabled
        logger.info("AWS Business or Enterprise Support is enabled")
        return True, "AWS Business or Enterprise Support is enabled. The full set of Trusted Advisor checks is available."

    except ClientError as e:
        error_code = e.response.get('Error', {}).get('Code')
        if error_code == 'SubscriptionRequiredException':
            logger.info("AWS Business or Enterprise Support is not enabled")
            return False, "AWS Business or Enterprise Support is not enabled. To unlock the full set of Trusted Advisor checks, upgrade to Business or Enterprise Support."
        else:
            logger.warning(f"Error checking AWS Support subscription: {e}")
            return None, f"Could not determine AWS Support subscription status: {error_code}"
    except Exception as e:
        logger.warning(f"Error checking AWS Support subscription: {e}")
        return None, f"Could not determine AWS Support subscription status: {str(e)}"
def get_resource_tags(resource_type, resource_id):
    """
    Get tags for a specific AWS resource, focusing on the Name tag.

    Args:
        resource_type: The type of the AWS resource
        resource_id: The ID of the AWS resource

    Returns:
        The value of the Name tag, or None if not found
    """
    try:
        # Initialize the resource-groups-tagging-api client
        tagging_client = boto3.client('resourcegroupstaggingapi')

        # Construct the ARN based on resource type and ID
        # This is a simplified approach and may need to be adjusted for certain resource types
        if resource_type.startswith('AWS::'):
            resource_type_short = resource_type[5:]  # Remove 'AWS::' prefix
        else:
            resource_type_short = resource_type

        # Handle special cases for ARN construction
        if resource_type_short == 'EC2::Instance':
            arn = f"arn:aws:ec2:{boto3.session.Session().region_name}:{boto3.client('sts').get_caller_identity()['Account']}:instance/{resource_id}"
        elif resource_type_short == 'S3::Bucket':
            arn = f"arn:aws:s3:::{resource_id}"
        else:
            # Generic ARN format for most resources
            service = resource_type_short.split('::')[0].lower()
            resource_path = resource_type_short.split('::')[1].lower()
            arn = f"arn:aws:{service}:{boto3.session.Session().region_name}:{boto3.client('sts').get_caller_identity()['Account']}:{resource_path}/{resource_id}"

        # Get tags for the resource
        response = tagging_client.get_resources(
            ResourceARNList=[arn]
        )

        # Extract the Name tag if it exists
        for resource_tag_mapping in response.get('ResourceTagMappingList', []):
            tags = resource_tag_mapping.get('Tags', [])
            for tag in tags:
                if tag.get('Key') == 'Name':
                    return tag.get('Value')

        return None
    except Exception as e:
        logger.debug(f"Error getting tags for resource {resource_type} {resource_id}: {e}")
        return None
