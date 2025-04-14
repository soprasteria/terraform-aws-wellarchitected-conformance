import boto3
import logging
from datetime import datetime

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)


# Initialize AWS clients
logger.info("Initializing AWS clients")
config = boto3.client('config')
budgets = boto3.client('budgets')
organizations = boto3.client('organizations')

# Create a formatter
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')

# Add handler if running locally (Lambda automatically adds a handler)
if not logger.handlers:
    handler = logging.StreamHandler()
    handler.setFormatter(formatter)
    logger.addHandler(handler)

evaluations = []

try:
    def check_compliance(budgets, organizations, event):
        try:
            logger.info("Starting compliance check")

            # First check if account is part of an organization with consolidated billing
            logger.info("Retrieving organization information")
            org_info = organizations.describe_organization()
            current_account = event['accountId']
            logger.info(f"Checking compliance for account: {current_account}")

            # Check if account is a member account (not management account)
            is_member = org_info['Organization']['MasterAccountId'] != current_account
            logger.info(f"Account is member account: {is_member}")

            # Check if consolidated billing is enabled
            has_consolidated_billing = org_info['Organization']['FeatureSet'] in ['CONSOLIDATED_BILLING', 'ALL']
            logger.info(f"Account has consolidated billing enabled: {has_consolidated_billing}")

            # If not a member account with consolidated billing, return NON_COMPLIANT
            if not (is_member and has_consolidated_billing):
                logger.warning("Account does not meet compliance requirements")
                return 'NON_COMPLIANT'

            logger.info("Account meets all compliance requirements")
            return 'COMPLIANT'

        except organizations.exceptions.AWSOrganizationsNotInUseException:
            logger.warning("Account is not part of an organization")
            return 'NON_COMPLIANT'
        except Exception as e:
            logger.error(f"Error checking compliance: {str(e)}", exc_info=True)
            return 'NON_COMPLIANT'

    def lambda_handler(event, context):
        try:
            logger.info("Starting Lambda handler execution")
            compliance_type = check_compliance(budgets, organizations, event)

            # Create evaluation result
            logger.info("Creating evaluation result")
            evaluation = {
                'ComplianceResourceType': 'AWS::::Account',
                'ComplianceResourceId': event['accountId'],
                'ComplianceType': compliance_type,
                'OrderingTimestamp': datetime.now()
            }
            evaluations.append(evaluation)

            # Report results back to AWS Config
            logger.info("Sending evaluation results to AWS Config")
            config.put_evaluations(
                Evaluations=evaluations,
                ResultToken=event['resultToken']
            )

            logger.info(f"Evaluation complete with status: {compliance_type}")
            return {
                'statusCode': 200,
                'body': f'Evaluation complete. Compliance status: {compliance_type}'
            }

        except Exception as e:
            logger.error(f"Error in lambda_handler: {str(e)}", exc_info=True)
            raise

except Exception as e:
    logger.error(f"Error evaluating compliance: {str(e)}", exc_info=True)
    raise
