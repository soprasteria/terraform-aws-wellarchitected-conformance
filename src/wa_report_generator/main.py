"""
Well-Architected Report Generator Lambda Function

This Lambda function generates an HTML report from AWS Config Conformance Packs
compliance data and uploads it to an S3 bucket.

Environment Variables:
    LOG_LEVEL: Logging level (default: INFO)
    SECURITY_CONFORMANCE_PACK: Name of the Security conformance pack
    RELIABILITY_CONFORMANCE_PACK: Name of the Reliability conformance pack
    COST_OPTIMIZATION_CONFORMANCE_PACK: Name of the Cost Optimization conformance pack
    S3_BUCKET_NAME: Name of the S3 bucket to store HTML reports
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

def collect_compliance_data(conformance_packs):
    """
    Collect compliance data from all conformance packs for HTML report generation.
    
    Args:
        conformance_packs: List of conformance pack names to process
        
    Returns:
        Dictionary with compliance data organized by pillar and best practice
    """
    compliance_data = {}
    
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
            
        # Initialize pillar data if not exists
        if pillar_name not in compliance_data:
            compliance_data[pillar_name] = {}
            
        # Get conformance pack rules
        rules = get_conformance_pack_details(conformance_pack_name)
        
        for rule in rules:
            rule_name = rule.get('ConfigRuleName')
            compliance_type = rule.get('Compliance', {}).get('ComplianceType')
            
            # Extract best practice ID from rule name (e.g., SEC01, REL02)
            best_practice_id = None
            for prefix in ['SEC', 'REL', 'COST']:
                if prefix in rule_name:
                    # Find the position of the prefix
                    idx = rule_name.find(prefix)
                    # Extract the prefix and the following digits
                    potential_id = rule_name[idx:idx+5]  # Assuming format like SEC01
                    if potential_id[3:].isdigit():
                        best_practice_id = potential_id
                        break
            
            if not best_practice_id:
                logger.warning(f"Could not extract best practice ID from rule name: {rule_name}")
                continue
                
            # Initialize best practice data if not exists
            if best_practice_id not in compliance_data[pillar_name]:
                compliance_data[pillar_name][best_practice_id] = {
                    'title': f"Best Practice {best_practice_id}",
                    'resources': []
                }
                
            # Get rule details including resources
            evaluation_results = get_rule_details(rule_name)
            
            for result in evaluation_results:
                resource_type = result.get('EvaluationResultIdentifier', {}).get('EvaluationResultQualifier', {}).get('ResourceType')
                resource_id = result.get('EvaluationResultIdentifier', {}).get('EvaluationResultQualifier', {}).get('ResourceId')
                resource_compliance = result.get('ComplianceType')
                
                compliance_data[pillar_name][best_practice_id]['resources'].append({
                    'resource_type': resource_type,
                    'resource_id': resource_id,
                    'compliance_status': resource_compliance
                })
    
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
        generation_time=datetime.now(timezone).strftime("%Y-%m-%d %H:%M:%S %Z")
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
    workload_id = event.get('workload_id')  # Not used but included for compatibility
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
    conformance_packs = [
        SECURITY_CONFORMANCE_PACK,
        RELIABILITY_CONFORMANCE_PACK,
        COST_OPTIMIZATION_CONFORMANCE_PACK
    ]

    try:
        # Get AWS account ID and region
        account_id = sts_client.get_caller_identity()['Account']
        region = boto3.session.Session().region_name
        
        # Collect compliance data
        logger.info("Collecting compliance data from AWS Config")
        compliance_data = collect_compliance_data(conformance_packs)
        
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
