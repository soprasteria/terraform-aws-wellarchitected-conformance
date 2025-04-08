import boto3
import json
import logging
import os
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

def get_question_mapping(workload_id, pillar):
    """
    Dynamically generate question mapping by listing answers for the pillar
    and creating a dictionary of question IDs for later matching with AWS Config rules.

    Args:
        workload_id: The Well-Architected workload ID
        pillar: The pillar name (security, reliability, costOptimization)

    Returns:
        A dictionary of question IDs for the specified pillar
    """
    lens_alias = "wellarchitected"
    question_ids = {}

    try:
        # Get all questions for this pillar - pagination not supported for list_answers
        response = wellarchitected_client.list_answers(
            WorkloadId=workload_id,
            LensAlias=lens_alias,
            PillarId=pillar,
            MaxResults=50
        )

        # Get the answers from the response
        all_questions = response.get('AnswerSummaries', [])
        logger.info(f"Retrieved {len(all_questions)} questions for pillar {pillar}")

        # Store all question IDs for this pillar
        for question in all_questions:
            question_id = question.get('QuestionId')
            if question_id:
                # Store the question ID itself as the key for direct matching with rule names
                question_ids[question_id] = question_id
                logger.info(f"Added question ID {question_id} for pillar {pillar}")

        logger.info(f"Generated {len(question_ids)} question IDs for pillar {pillar}")
        return question_ids

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

def update_wellarchitected_notes(workload_id, lens_alias, question_id, notes, rule_name, dry_run=True):
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

        # Update the notes, preserving existing content but replacing previous evaluation for this rule
        current_notes = response.get('Answer', {}).get('Notes', '')
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # Define start and end markers for this rule's evaluation results
        start_marker = f"<!-- BEGIN_{rule_name} -->"
        end_marker = f"<!-- END_{rule_name} -->"

        # Check if we already have evaluation results for this rule
        start_idx = current_notes.find(start_marker)
        end_idx = current_notes.find(end_marker)

        if start_idx >= 0 and end_idx >= 0 and end_idx > start_idx:
            # Replace existing evaluation results for this rule
            before_section = current_notes[:start_idx]
            after_section = current_notes[end_idx + len(end_marker):]
            new_section = f"{start_marker}\nLast update: {timestamp}\n{notes}\n{end_marker}"
            updated_notes = f"{before_section}{new_section}{after_section}"
        else:
            # Add new evaluation results
            new_section = f"\n\n{start_marker}\nLast update: {timestamp}\n{notes}\n{end_marker}"
            updated_notes = f"{current_notes}{new_section}"

        # Check if the updated notes exceed the character limit
        if len(updated_notes) > 2080:
            logger.error(f"Updated notes for question {question_id} exceed the 2080 character limit: {len(updated_notes)} characters")
            # Truncate the notes to fit within the limit
            updated_notes = updated_notes[:2070] + "..."

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

def process_conformance_pack(conformance_pack_name, workload_id, dry_run=True):
    """Process a conformance pack and update the Well-Architected Tool."""
    logger.info(f"Processing conformance pack: {conformance_pack_name}")
    lens_alias = "wellarchitected"

    # Extract pillar from conformance pack name
    pillar = None
    for prefix, pillar_name in PILLAR_MAPPING.items():
        if prefix in conformance_pack_name:
            pillar = pillar_name
            break

    if not pillar:
        logger.warning(f"Could not determine pillar for conformance pack: {conformance_pack_name}")
        return

    # Get all question IDs for this pillar
    question_ids = get_question_mapping(workload_id, pillar)

    if not question_ids:
        logger.warning(f"No question IDs retrieved for pillar: {pillar}")
        return

    # Get conformance pack rules
    rules = get_conformance_pack_details(conformance_pack_name)

    for rule in rules:
        rule_name = rule.get('ConfigRuleName')
        compliance_type = rule.get('Compliance', {}).get('ComplianceType')

        # Find matching question ID for this rule
        matching_question_id = None
        for question_id in question_ids:
            # Check if the question ID appears in the rule name
            if question_id in rule_name:
                matching_question_id = question_id
                logger.info(f"Found matching question ID {matching_question_id} for rule {rule_name}")
                break

        # If no direct match found, try to find any question ID that is a substring of the rule name
        if not matching_question_id:
            for question_id in question_ids:
                # Extract parts of the question ID to check for partial matches
                parts = question_id.split('.')
                for part in parts:
                    if part and len(part) > 3 and part in rule_name:  # Avoid matching very short strings
                        matching_question_id = question_id
                        logger.info(f"Found partial match with question ID {matching_question_id} (part: {part}) for rule {rule_name}")
                        break
                if matching_question_id:
                    break

        if not matching_question_id:
            logger.warning(f"No matching question ID found for rule: {rule_name}")
            continue

        # Get rule details including resources
        evaluation_results = get_rule_details(rule_name)

        # Prepare notes
        notes = [""]

        if not evaluation_results:
            notes.append("No resources evaluated.\n")
        else:
            for result in evaluation_results:
                resource_type = result.get('EvaluationResultIdentifier', {}).get('EvaluationResultQualifier', {}).get('ResourceType')
                resource_id = result.get('EvaluationResultIdentifier', {}).get('EvaluationResultQualifier', {}).get('ResourceId')
                resource_compliance = result.get('ComplianceType')

                notes.append(f"- {resource_compliance}, {resource_type}, {resource_id}\n")

        notes_content = ''.join(notes)

        # Check if notes exceed character limit
        if len(notes_content) > 2080:
            logger.error(f"Notes for rule {rule_name} exceed the 2080 character limit: {len(notes_content)} characters")
            # Truncate the notes to fit within the limit
            notes_content = notes_content[:2070] + "..."

        # Update Well-Architected Tool
        update_wellarchitected_notes(workload_id, lens_alias, matching_question_id, notes_content, rule_name, dry_run)

def clean_all_notes(workload_id, dry_run=True):
    """
    Clean all notes for a workload by setting them to empty strings.

    Args:
        workload_id: The Well-Architected workload ID
        dry_run: Whether to run in dry-run mode (no actual updates)

    Returns:
        Boolean indicating success or failure
    """
    lens_alias = "wellarchitected"
    success = True

    try:
        # Get all pillars for this workload
        pillars = ["security", "reliability", "costOptimization", "operationalExcellence", "performance", "sustainability"]

        for pillar in pillars:
            logger.info(f"Cleaning notes for pillar: {pillar}")

            try:
                # Get all questions for this pillar
                response = wellarchitected_client.list_answers(
                    WorkloadId=workload_id,
                    LensAlias=lens_alias,
                    PillarId=pillar,
                    MaxResults=50
                )

                questions = response.get('AnswerSummaries', [])
                logger.info(f"Found {len(questions)} questions for pillar {pillar}")

                for question in questions:
                    question_id = question.get('QuestionId')
                    if not question_id:
                        continue

                    if dry_run:
                        logger.info(f"DRY RUN: Would clear notes for question {question_id} in pillar {pillar}")
                    else:
                        try:
                            # Update the answer with empty notes
                            wellarchitected_client.update_answer(
                                WorkloadId=workload_id,
                                LensAlias=lens_alias,
                                QuestionId=question_id,
                                Notes=""
                            )
                            logger.info(f"Successfully cleared notes for question {question_id} in pillar {pillar}")
                        except ClientError as e:
                            logger.error(f"Error clearing notes for question {question_id} in pillar {pillar}: {e}")
                            success = False

            except ClientError as e:
                logger.error(f"Error listing answers for pillar {pillar}: {e}")
                success = False

        return success
    except Exception as e:
        logger.error(f"Unexpected error cleaning notes: {e}")
        return False

def lambda_handler(event, context):
    """Lambda handler function."""
    logger.info(f"Event received: {json.dumps(event)}")

    # Get parameters from event
    workload_id = event.get('workload_id')
    dry_run = event.get('dry_run', True)
    clean_notes = event.get('clean_notes', False)

    if not workload_id:
        return {
            'statusCode': 400,
            'body': json.dumps('workload_id parameter is required')
        }

    # If clean_notes is True, clear all notes for the workload
    if clean_notes:
        logger.info(f"Clean notes mode enabled. Will clear all notes for workload {workload_id}")
        if clean_all_notes(workload_id, dry_run):
            return {
                'statusCode': 200,
                'body': json.dumps('Well-Architected Tool notes cleaned successfully')
            }
        else:
            return {
                'statusCode': 500,
                'body': json.dumps('Failed to clean Well-Architected Tool notes')
            }

    # List of conformance packs to process from environment variables
    conformance_packs = [
        SECURITY_CONFORMANCE_PACK,
        RELIABILITY_CONFORMANCE_PACK,
        COST_OPTIMIZATION_CONFORMANCE_PACK
    ]

    logger.info(f"Processing conformance packs: {conformance_packs}")
    logger.info(f"Running in {'dry-run' if dry_run else 'live'} mode")

    for pack in conformance_packs:
        process_conformance_pack(pack, workload_id, dry_run)

    return {
        'statusCode': 200,
        'body': json.dumps('Well-Architected Tool update completed')
    }