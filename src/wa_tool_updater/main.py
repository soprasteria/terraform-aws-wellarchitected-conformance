import boto3
import json
import logging
import os
from datetime import datetime
from botocore.exceptions import ClientError
from collections import defaultdict

"""
Well-Architected Tool Updater Lambda Function

This Lambda function updates a Well-Architected Tool workload with compliance data
from AWS Config Conformance Packs. It processes each conformance pack (Security,
Reliability, Cost Optimization), groups all rules by question ID, and updates
each question in the Well-Architected Tool workload with consolidated resource
compliance information.

Environment Variables:
    LOG_LEVEL: Logging level (default: INFO)
    SECURITY_CONFORMANCE_PACK: Name of the Security conformance pack
    RELIABILITY_CONFORMANCE_PACK: Name of the Reliability conformance pack
    COST_OPTIMIZATION_CONFORMANCE_PACK: Name of the Cost Optimization conformance pack

Event Parameters:
    workload_id: ID of the Well-Architected Tool workload to update
    dry_run: Whether to run in dry-run mode (no actual updates)
    clean_notes: Whether to clean all notes before updating
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

# Maximum character limit for Well-Architected Tool notes
MAX_NOTES_LENGTH = 2080
# Safety margin for notes to ensure we don't exceed the limit
NOTES_SAFETY_MARGIN = 30

def count_resources_by_type(evaluation_results):
    """
    Group resources by type and compliance status, returning counts for each.

    Args:
        evaluation_results: List of evaluation results from AWS Config

    Returns:
        Dictionary with resource type counts by compliance status
    """
    resource_counts = {}

    for result in evaluation_results:
        resource_type = result.get('EvaluationResultIdentifier', {}).get('EvaluationResultQualifier', {}).get('ResourceType')
        resource_compliance = result.get('ComplianceType')

        if not resource_type:
            continue

        if resource_type not in resource_counts:
            resource_counts[resource_type] = {'COMPLIANT': 0, 'NON_COMPLIANT': 0}

        if resource_compliance in resource_counts[resource_type]:
            resource_counts[resource_type][resource_compliance] += 1

    return resource_counts

def generate_summarized_notes_for_rule(rule_data):
    """
    Generate summarized notes with resource counts by type instead of individual resources.
    Skip rules with no resources evaluated.

    For summarized format:
    - Show counts of resources by type
    - Skip rules with no resources

    Args:
        rule_data: Dictionary containing rule name, compliance type, and evaluation results

    Returns:
        String with summarized notes content or None if no resources evaluated
    """
    rule_name = rule_data['rule_name']
    compliance_type = rule_data['compliance_type']
    evaluation_results = rule_data['evaluation_results']

    # Skip rules with no resources evaluated
    if not evaluation_results:
        return None

    # Get counts by resource type
    resource_counts = count_resources_by_type(evaluation_results)

    # Skip rules with no resources in scope (could happen if resource types couldn't be determined)
    if not resource_counts:
        return None

    notes = []
    notes.append(f"**{rule_name}**\n")

    # Add non-compliant resources first (by type)
    non_compliant_types = []
    for resource_type, counts in resource_counts.items():
        if counts['NON_COMPLIANT'] > 0:
            non_compliant_types.append(f"- {resource_type}: {counts['NON_COMPLIANT']} resources")

    if non_compliant_types:
        notes.append("[!] Non-compliant:\n")
        notes.extend(f"{item}\n" for item in non_compliant_types)
        notes.append("\n")

    # Add compliant resources (by type)
    compliant_types = []
    for resource_type, counts in resource_counts.items():
        if counts['COMPLIANT'] > 0:
            compliant_types.append(f"- {resource_type}: {counts['COMPLIANT']} resources")

    if compliant_types:
        notes.append("[+] Compliant:\n")
        notes.extend(f"{item}\n" for item in compliant_types)
        notes.append("\n")

    return ''.join(notes)

def generate_summarized_notes_for_question(rules_data):
    """
    Generate summarized notes for all rules associated with a question.
    Skip rules with no resources evaluated.

    Args:
        rules_data: List of dictionaries containing rule data

    Returns:
        String with summarized notes content for all rules with resources
    """
    all_notes = []

    for rule_data in rules_data:
        rule_notes = generate_summarized_notes_for_rule(rule_data)
        if rule_notes:  # Only include rules that have resources
            all_notes.append(rule_notes)

    return ''.join(all_notes)

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
                logger.debug(f"Added question ID {question_id} for pillar {pillar}")

        logger.info(f"Generated {len(question_ids)} question IDs for pillar {pillar}")
        return question_ids

    except ClientError as e:
        logger.error(f"Error generating question mapping for pillar {pillar}: {e}")
        return {}

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

    except ClientError as e:
        logger.error(f"Error getting conformance pack details: {e}")
        return []
    except Exception as e:
        logger.error(f"Unexpected error in get_conformance_pack_details: {e}")
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
    except ClientError as e:
        logger.error(f"Error getting rule details: {e}")
        return []

def update_wellarchitected_notes(workload_id, lens_alias, question_id, consolidated_notes, dry_run=True):
    """Update notes for a specific question in the Well-Architected Tool with consolidated information."""
    if dry_run:
        logger.info(f"DRY RUN: Would update question {question_id} with consolidated notes")
        return True

    try:
        # First, get the current answer
        response = wellarchitected_client.get_answer(
            WorkloadId=workload_id,
            LensAlias=lens_alias,
            QuestionId=question_id
        )

        # Get current notes
        current_notes = response.get('Answer', {}).get('Notes', '')

        # Get timestamp for the report
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # Define minimal markers for our automated updates - include timestamp in the start marker
        start_marker = f"<!-- WA-{timestamp} -->"
        end_marker = "<!-- /WA -->"

        # Check if we already have evaluation results - look for the generic part of the marker
        start_idx = current_notes.find("<!-- WA-")
        end_idx = current_notes.find(end_marker)

        # Create the new section with the report content - no extra headers to save space
        new_section = f"{start_marker}\n{consolidated_notes}\n{end_marker}"

        if start_idx >= 0 and end_idx >= 0 and end_idx > start_idx:
            # Replace existing evaluation results
            before_section = current_notes[:start_idx]
            after_section = current_notes[end_idx + len(end_marker):]
            updated_notes = f"{before_section}{new_section}{after_section}"
        else:
            # Add new evaluation results
            separator = "\n\n" if current_notes else ""
            updated_notes = f"{current_notes}{separator}{new_section}"

        # Check if the updated notes exceed the character limit
        if len(updated_notes) > MAX_NOTES_LENGTH - NOTES_SAFETY_MARGIN:
            logger.warning(f"Updated notes for question {question_id} exceed the character limit: {len(updated_notes)} characters")

            # Switch to summarized format for all rules in this question
            # This is handled by the caller who will pass in summarized notes instead

            # Ensure we don't exceed the limit even with summarized notes
            if len(updated_notes) > MAX_NOTES_LENGTH - NOTES_SAFETY_MARGIN:
                # Calculate safe length to ensure we have room for the markers and truncation message
                safe_length = MAX_NOTES_LENGTH - len(start_marker) - len(end_marker) - 100

                if start_idx >= 0 and end_idx >= 0 and end_idx > start_idx:
                    # If we have existing sections, preserve the structure but truncate the new section
                    before_section = current_notes[:start_idx]
                    after_section = current_notes[end_idx + len(end_marker):]

                    # Calculate how much space we have for the new section
                    available_space = MAX_NOTES_LENGTH - NOTES_SAFETY_MARGIN - len(before_section) - len(after_section) - len(start_marker) - len(end_marker)

                    if available_space > 100:
                        # We have enough space for a truncated summary
                        truncated_content = consolidated_notes[:available_space - 50]
                        truncated_content += "\n[Content truncated due to size limits]"
                        updated_notes = f"{before_section}{start_marker}\n{truncated_content}\n{end_marker}{after_section}"
                    else:
                        # Not enough space even for a summary
                        updated_notes = f"{before_section}{start_marker}\n[Content truncated due to size limits]\n{end_marker}{after_section}"
                else:
                    # No existing sections
                    truncated_notes = current_notes[:safe_length] if current_notes else ""
                    updated_notes = f"{truncated_notes}\n{start_marker}\n[Content truncated due to size limits]\n{end_marker}"

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

                    # Use update_wellarchitected_notes function with empty notes
                    if not update_wellarchitected_notes(
                        workload_id=workload_id,
                        lens_alias=lens_alias,
                        question_id=question_id,
                        consolidated_notes="",
                        dry_run=dry_run
                    ):
                        logger.error(f"Failed to clear notes for question {question_id} in pillar {pillar}")
                        success = False

            except ClientError as e:
                logger.error(f"Error listing answers for pillar {pillar}: {e}")
                success = False

        return success
    except Exception as e:
        logger.error(f"Unexpected error cleaning notes: {e}")
        return False

def process_conformance_pack(conformance_pack_name, workload_id, dry_run=True):
    """
    Process a conformance pack, group rules by question ID, and update the Well-Architected Tool
    with consolidated information for each question.

    For detailed format (when within character limits):
    - Show all non-compliant resources with their IDs
    - Show only the count of compliant resources
    - Skip rules with no resources

    For summarized format (when exceeding character limits):
    - Show counts of resources by type
    - Skip rules with no resources
    """
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

    # Dictionary to group rules and their results by question ID
    question_rule_mapping = defaultdict(list)

    # First pass: match rules to questions and collect them
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

        # Add this rule and its results to the question's collection
        question_rule_mapping[matching_question_id].append({
            'rule_name': rule_name,
            'compliance_type': compliance_type,
            'evaluation_results': evaluation_results
        })

    # Second pass: process each question and update with consolidated information
    for question_id, rules_data in question_rule_mapping.items():
        # First try to generate detailed notes with all resource information
        consolidated_notes = []

        for rule_data in rules_data:
            rule_name = rule_data['rule_name']
            compliance_type = rule_data['compliance_type']
            evaluation_results = rule_data['evaluation_results']

            # Skip rules with no resources evaluated
            if not evaluation_results:
                continue

            # Add rule header - more compact format
            consolidated_notes.append(f"**{rule_name}**\n")

            # Group results by compliance type for better readability
            compliant_resources = []
            non_compliant_resources = []

            for result in evaluation_results:
                resource_type = result.get('EvaluationResultIdentifier', {}).get('EvaluationResultQualifier', {}).get('ResourceType')
                resource_id = result.get('EvaluationResultIdentifier', {}).get('EvaluationResultQualifier', {}).get('ResourceId')
                resource_compliance = result.get('ComplianceType')

                resource_info = f"{resource_type}: {resource_id}"

                if resource_compliance == 'COMPLIANT':
                    compliant_resources.append(resource_info)
                elif resource_compliance == 'NON_COMPLIANT':
                    non_compliant_resources.append(resource_info)

            # Add non-compliant resources first as they're more important
            if non_compliant_resources:
                consolidated_notes.append("[!] Non-compliant:\n")
                for resource in non_compliant_resources:
                    consolidated_notes.append(f"- {resource}\n")
                consolidated_notes.append("\n")

            # For compliant resources, just show the count to save space
            if compliant_resources:
                consolidated_notes.append(f"[+] {len(compliant_resources)} compliant resources\n\n")
        # Convert list of strings to a single string
        detailed_notes = ''.join(consolidated_notes)

        # Check if the detailed notes would exceed the character limit
        # First, get the current answer to check the total length
        try:
            response = wellarchitected_client.get_answer(
                WorkloadId=workload_id,
                LensAlias=lens_alias,
                QuestionId=question_id
            )
            current_notes = response.get('Answer', {}).get('Notes', '')

            # Calculate the total length with detailed notes
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            start_marker = f"<!-- WA-{timestamp} -->"
            end_marker = "<!-- /WA -->"

            # Estimate the total length
            estimated_length = len(current_notes) + len(detailed_notes) + len(start_marker) + len(end_marker) + 20

            # If the estimated length exceeds the limit, switch to summarized format
            if estimated_length > MAX_NOTES_LENGTH - NOTES_SAFETY_MARGIN:
                logger.info(f"Switching to summarized format for question {question_id} due to length constraints")
                summarized_notes = generate_summarized_notes_for_question(rules_data)
                update_wellarchitected_notes(workload_id, lens_alias, question_id, summarized_notes, dry_run)
            else:
                # Use detailed notes
                update_wellarchitected_notes(workload_id, lens_alias, question_id, detailed_notes, dry_run)

        except ClientError as e:
            logger.error(f"Error checking notes length for question {question_id}: {e}")
            # Fall back to summarized format
            summarized_notes = generate_summarized_notes_for_question(rules_data)
            update_wellarchitected_notes(workload_id, lens_alias, question_id, summarized_notes, dry_run)

def lambda_handler(event, context):
    """
    Lambda function handler that processes conformance packs and updates the Well-Architected Tool.

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

    for conformance_pack in conformance_packs:
        process_conformance_pack(conformance_pack, workload_id, dry_run)

    logger.info("Well-Architected Tool updater completed successfully")
    return {
        'statusCode': 200,
        'body': json.dumps({
            'status': 'success',
            'message': 'Well-Architected Tool updated successfully',
            'dry_run': dry_run
        })
    }
