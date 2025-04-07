import boto3
import json
import logging
import os
import re
from datetime import datetime
from botocore.exceptions import ClientError

"""
Well-Architected Tool Updater Lambda Function

This Lambda function updates a Well-Architected Tool workload with compliance data
from AWS Config Conformance Packs. It processes each conformance pack (Security,
Reliability, Cost Optimization), loops through all rules in sequence, and updates
the corresponding question in the Well-Architected Tool workload with resource
compliance information.

Environment Variables:
    LOG_LEVEL: Logging level (default: INFO)
    SECURITY_CONFORMANCE_PACK: Name of the Security conformance pack
    RELIABILITY_CONFORMANCE_PACK: Name of the Reliability conformance pack
    COST_OPTIMIZATION_CONFORMANCE_PACK: Name of the Cost Optimization conformance pack

Event Parameters:
    workload_id: ID of the Well-Architected Tool workload to update
    dry_run: Whether to run in dry-run mode (no actual updates)
"""

# Configure logging
logger = logging.getLogger()
log_level = os.environ.get('LOG_LEVEL', 'INFO')
logger.setLevel(getattr(logging, log_level))

# Initialize clients
config_client = boto3.client('config')
wellarchitected_client = boto3.client('wellarchitected')

# Get conformance pack names from environment variables
SECURITY_CONFORMANCE_PACK = os.environ.get('SECURITY_CONFORMANCE_PACK', 'Well-Architected-Security')
RELIABILITY_CONFORMANCE_PACK = os.environ.get('RELIABILITY_CONFORMANCE_PACK', 'Well-Architected-Reliability')
COST_OPTIMIZATION_CONFORMANCE_PACK = os.environ.get('COST_OPTIMIZATION_CONFORMANCE_PACK', 'Well-Architected-Cost-Optimization')

# Mapping of conformance pack names to Well-Architected pillars
PILLAR_MAPPING = {
    SECURITY_CONFORMANCE_PACK: 'security',
    RELIABILITY_CONFORMANCE_PACK: 'reliability',
    COST_OPTIMIZATION_CONFORMANCE_PACK: 'costOptimization'
}

# Rule prefix patterns for each pillar
RULE_PREFIX_PATTERNS = {
    'security': r'^SEC(\d+)',
    'reliability': r'^REL(\d+)',
    'costOptimization': r'^COST(\d+)'
}

def get_question_mapping(workload_id, pillar):
    """
    Dynamically generate question mapping by listing answers for the pillar
    and mapping them to numerical indices while preserving the original order
    from the Well-Architected Tool.

    Args:
        workload_id: The Well-Architected workload ID
        pillar: The pillar name (security, reliability, costOptimization)

    Returns:
        A dictionary mapping rule prefixes (e.g., SEC01) to question IDs
    """
    lens_alias = f"wellarchitected:{pillar}"
    question_mapping = {}

    try:
        # Get all questions for this pillar
        paginator = wellarchitected_client.get_paginator('list_answers')
        page_iterator = paginator.paginate(
            WorkloadId=workload_id,
            LensAlias=lens_alias
        )

        # Collect all questions while preserving their original order
        all_questions = []
        for page in page_iterator:
            all_questions.extend(page.get('AnswerSummaries', []))

        # The Well-Architected Tool API returns questions in their proper order
        # We'll use this order directly without sorting to preserve the intended structure
        logger.info(f"Retrieved {len(all_questions)} questions for pillar {pillar}")

        # Create mapping based on the pattern for this pillar
        prefix_pattern = RULE_PREFIX_PATTERNS.get(pillar)
        if not prefix_pattern:
            logger.warning(f"No rule prefix pattern defined for pillar: {pillar}")
            return {}

        # Get the prefix base (SEC, REL, COST)
        prefix_base = prefix_pattern[1:4]

        # Map each question to a numbered rule prefix (SEC01, SEC02, etc.)
        # using the original order from the Well-Architected Tool
        for i, question in enumerate(all_questions, start=1):
            question_id = question.get('QuestionId')
            if question_id:
                rule_prefix = f"{prefix_base}{i:02d}"  # Format as SEC01, SEC02, etc.
                question_mapping[rule_prefix] = question_id
                logger.debug(f"Mapped {rule_prefix} to question {question_id} (original position {i})")

        logger.info(f"Generated {len(question_mapping)} question mappings for pillar {pillar}")
        return question_mapping

    except ClientError as e:
        logger.error(f"Error generating question mapping for pillar {pillar}: {e}")
        return {}

def get_conformance_pack_details(conformance_pack_name):
    """Get details of a conformance pack including its rules."""
    try:
        response = config_client.describe_conformance_pack_compliance(
            ConformancePackName=conformance_pack_name
        )
        return response.get('ConformancePackRuleComplianceList', [])
    except ClientError as e:
        logger.error(f"Error getting conformance pack details: {e}")
        return []

def get_rule_details(rule_name):
    """Get details of a config rule including non-compliant resources."""
    try:
        response = config_client.get_compliance_details_by_config_rule(
            ConfigRuleName=rule_name,
            ComplianceTypes=['NON_COMPLIANT', 'COMPLIANT']
        )
        return response.get('EvaluationResults', [])
    except ClientError as e:
        logger.error(f"Error getting rule details: {e}")
        return []

def update_wellarchitected_notes(workload_id, lens_alias, question_id, notes, dry_run=True):
    """Update notes for a specific question in the Well-Architected Tool."""
    if dry_run:
        logger.info(f"DRY RUN: Would update question {question_id} with notes: {notes}")
        return True

    try:
        # First, get the current answer
        response = wellarchitected_client.get_answer(
            WorkloadId=workload_id,
            LensAlias=lens_alias,
            QuestionId=question_id
        )

        # Update the notes, preserving existing content
        current_notes = response.get('Answer', {}).get('Notes', '')
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        updated_notes = f"{current_notes}\n\n--- AWS Config Compliance Update: {timestamp} ---\n{notes}"

        # Update the answer with new notes
        wellarchitected_client.update_answer(
            WorkloadId=workload_id,
            LensAlias=lens_alias,
            QuestionId=question_id,
            Notes=updated_notes
        )

        logger.info(f"Successfully updated notes for question {question_id}")
        return True
    except ClientError as e:
        logger.error(f"Error updating Well-Architected Tool: {e}")
        return False

def extract_rule_prefix(rule_name):
    """Extract the rule prefix (e.g., SEC01) from a rule name."""
    # Look for patterns like SEC01, REL02, COST03, etc.
    patterns = [r'(SEC\d+)', r'(REL\d+)', r'(COST\d+)']

    for pattern in patterns:
        match = re.search(pattern, rule_name)
        if match:
            return match.group(1)

    return None

def process_conformance_pack(conformance_pack_name, workload_id, dry_run=True):
    """Process a conformance pack and update the Well-Architected Tool."""
    logger.info(f"Processing conformance pack: {conformance_pack_name}")

    # Extract pillar from conformance pack name
    pillar = None
    for prefix, pillar_name in PILLAR_MAPPING.items():
        if prefix.lower() in conformance_pack_name.lower():
            pillar = pillar_name
            break

    if not pillar:
        logger.warning(f"Could not determine pillar for conformance pack: {conformance_pack_name}")
        return

    # Dynamically generate question mapping for this pillar
    question_mapping = get_question_mapping(workload_id, pillar)

    if not question_mapping:
        logger.warning(f"No question mapping generated for pillar: {pillar}")
        return

    # Get conformance pack rules
    rules = get_conformance_pack_details(conformance_pack_name)

    # Sort rules by their prefix (SEC01, SEC02, etc.)
    sorted_rules = sorted(rules, key=lambda x: x.get('ConfigRuleName', ''))

    for rule in sorted_rules:
        rule_name = rule.get('ConfigRuleName')
        compliance_type = rule.get('Compliance', {}).get('ComplianceType')

        # Extract rule prefix (SEC01, REL02, etc.)
        rule_prefix = extract_rule_prefix(rule_name)

        if not rule_prefix:
            logger.warning(f"Could not extract rule prefix from rule name: {rule_name}")
            continue

        # Find the question ID based on rule prefix
        question_id = question_mapping.get(rule_prefix)

        if not question_id:
            logger.warning(f"No question ID mapping found for rule prefix: {rule_prefix}")
            continue

        # Get rule details including resources
        evaluation_results = get_rule_details(rule_name)

        # Prepare notes
        notes = f"Rule: {rule_name}\nCompliance Status: {compliance_type}\n\nResources:\n"

        if not evaluation_results:
            notes += "No resources evaluated.\n"
        else:
            for result in evaluation_results:
                resource_type = result.get('EvaluationResultIdentifier', {}).get('EvaluationResultQualifier', {}).get('ResourceType')
                resource_id = result.get('EvaluationResultIdentifier', {}).get('EvaluationResultQualifier', {}).get('ResourceId')
                resource_compliance = result.get('ComplianceType')

                notes += f"- Type: {resource_type}, ID: {resource_id}, Status: {resource_compliance}\n"

        # Update Well-Architected Tool
        update_wellarchitected_notes(workload_id, f"wellarchitected:{pillar}", question_id, notes, dry_run)

def lambda_handler(event, context):
    """Lambda handler function."""
    logger.info(f"Event received: {json.dumps(event)}")

    # Get parameters from event
    workload_id = event.get('workload_id')
    dry_run = event.get('dry_run', True)

    if not workload_id:
        return {
            'statusCode': 400,
            'body': json.dumps('workload_id parameter is required')
        }

    # List of conformance packs to process from environment variables
    conformance_packs = [
        SECURITY_CONFORMANCE_PACK,
        RELIABILITY_CONFORMANCE_PACK,
        COST_OPTIMIZATION_CONFORMANCE_PACK
    ]

    logger.info(f"Processing conformance packs: {conformance_packs}")

    for pack in conformance_packs:
        process_conformance_pack(pack, workload_id, dry_run)

    return {
        'statusCode': 200,
        'body': json.dumps('Well-Architected Tool update completed')
    }
