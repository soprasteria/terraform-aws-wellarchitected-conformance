"""
Collect compliance data from AWS Config Conformance Packs
for the Well-Architected Framework report.
"""

import logging
from typing import Dict, List, Any

logger = logging.getLogger()

def collect_compliance_data(config_client, conformance_packs, pillar_mapping):
    """
    Collect compliance data from all conformance packs for HTML report generation.
    
    Args:
        config_client: Boto3 AWS Config client
        conformance_packs: List of conformance pack names to process
        pillar_mapping: Dictionary mapping conformance pack names to pillar IDs
        
    Returns:
        Dictionary with compliance data organized by pillar and best practice
    """
    compliance_data = {}
    
    for conformance_pack_name in conformance_packs:
        # Extract pillar name for this conformance pack
        pillar_name = None
        for prefix, pillar_id in pillar_mapping.items():
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
        rules = get_conformance_pack_details(config_client, conformance_pack_name)
        
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
            evaluation_results = get_rule_details(config_client, rule_name)
            
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

def get_conformance_pack_details(config_client, conformance_pack_name):
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

def get_rule_details(config_client, rule_name):
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
