"""
Lambda function for Well-Architected Tool Updater

This Lambda function updates a Well-Architected Tool workload with compliance data
from AWS Config Conformance Packs and generates an HTML report.
"""

import boto3
import json
import logging
import os
import pytz
from datetime import datetime
from botocore.exceptions import ClientError
from collections import defaultdict

# Import the report generator and HTML generator modules
from html_report_generator import generate_html_report, upload_report_to_s3
from report_generator import generate_and_upload_report

# Configure logging
logger = logging.getLogger()
log_level = os.environ.get('LOG_LEVEL', 'INFO')
logger.setLevel(getattr(logging, log_level))

# Initialize clients
config_client = boto3.client('config')
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

# Maximum character limit for Well-Architected Tool notes
MAX_NOTES_LENGTH = 2080
# Safety margin for notes to ensure we don't exceed the limit
NOTES_SAFETY_MARGIN = 10

def lambda_handler(event, context):
    """
    Lambda function handler that processes conformance packs and updates the Well-Architected Tool.
    Also generates an HTML report and uploads it to S3.

    Args:
        event: Lambda event object containing parameters
        context: Lambda context object

    Returns:
        Dictionary with status and message
    """
    logger.info("Starting Well-Architected Tool updater")

    # Get parameters from the event
    workload_id = event.get('workload_id')
    dry_run = event.get('dry_run', True)
    clean_notes = event.get('clean_notes', False)
    generate_report = event.get('generate_report', True)

    if not workload_id:
        error_msg = "No workload_id provided in the event"
        logger.error(error_msg)
        return {
            'statusCode': 400,
            'body': json.dumps({
                'status': 'error',
                'message': error_msg
            })
        }

    # Clean all notes if requested
    if clean_notes:
        logger.info(f"Cleaning all notes for workload {workload_id}")
        if not clean_all_notes(workload_id, dry_run):
            error_msg = "Failed to clean notes"
            logger.error(error_msg)
            return {
                'statusCode': 500,
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

    # Update Well-Architected Tool with compliance data
    for conformance_pack in conformance_packs:
        process_conformance_pack(conformance_pack, workload_id, dry_run)

    # Generate HTML report if requested
    report_url = ""
    if generate_report and S3_BUCKET_NAME:
        logger.info(f"Generating HTML report and uploading to S3 bucket: {S3_BUCKET_NAME}")
        report_url = generate_and_upload_report(
            config_client=config_client,
            conformance_packs=conformance_packs,
            pillar_mapping=PILLAR_MAPPING,
            bucket_name=S3_BUCKET_NAME,
            html_generator=generate_html_report,
            s3_uploader=upload_report_to_s3
        )

    logger.info("Well-Architected Tool updater completed successfully")
    return {
        'statusCode': 200,
        'body': json.dumps({
            'status': 'success',
            'message': 'Well-Architected Tool updated successfully',
            'dry_run': dry_run,
            'report_url': report_url
        })
    }

# Import the rest of the functions from main.py
# This would include:
# - count_resources_by_type
# - generate_summarized_notes_for_rule
# - generate_summarized_notes_for_question
# - get_question_mapping
# - get_conformance_pack_details
# - get_rule_details
# - update_wellarchitected_notes
# - clean_all_notes
# - process_conformance_pack
