import boto3
import logging
from datetime import datetime

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

evaluations = []

try:
    def check_compliance(budgets, organizations, event):
        try:
            # First check if account is part of an organization with consolidated billing
            logger.info("Checking organization information")
            org_info = organizations.describe_organization()
            current_account = event['accountId']
            logger.info(f"Checking compliance for account: {current_account}")

            # Check if account is a member account (not management account)
            is_member = org_info['Organization']['MasterAccountId'] != current_account
            logger.info(f"Account is member account: {is_member}")

            if not is_member:
                logger.warning("Account does not meet compliance requirements - not a member account")
                return 'NON_COMPLIANT'

            # Check for effective tag policy
            try:
                logger.info("Checking for effective tag policy")
                tag_policy_response = organizations.describe_effective_policy(
                    PolicyType='TAG_POLICY'
                )

                if tag_policy_response and 'EffectivePolicy' in tag_policy_response:
                    logger.info("Tag policy is applied to the account")
                    return 'COMPLIANT'
                else:
                    logger.warning("No effective tag policy found")
                    return 'NON_COMPLIANT'

            except organizations.exceptions.EffectivePolicyNotFoundException:
                logger.warning("No effective tag policy found for the account")
                return 'NON_COMPLIANT'
            except organizations.exceptions.PolicyNotFoundException:
                logger.warning("No tag policy found for the account")
                return 'NON_COMPLIANT'
            except organizations.exceptions.PolicyTypeNotEnabledException:
                logger.warning("Tag policies are not enabled in the organization")
                return 'NON_COMPLIANT'
            except Exception as e:
                logger.error(f"Error checking tag policy: {str(e)}", exc_info=True)
                return 'NON_COMPLIANT'


            except organizations.exceptions.PolicyNotFoundException:
                logger.warning("No tag policy found for the account")
                return 'NON_COMPLIANT'
            except organizations.exceptions.PolicyTypeNotEnabledException:
                logger.warning("Tag policies are not enabled in the organization")
                return 'NON_COMPLIANT'

        except organizations.exceptions.AWSOrganizationsNotInUseException:
            logger.warning("Account is not part of an organization")
            return 'NON_COMPLIANT'
        except Exception as e:
            logger.error(f"Error checking compliance: {str(e)}", exc_info=True)
            return 'NON_COMPLIANT'

    def lambda_handler(event, context):
        try:
            logger.info("Starting Lambda handler execution")

            # Initialize AWS Config and Budgets clients
            logger.info("Initializing AWS clients")
            config = boto3.client('config')
            budgets = boto3.client('budgets')
            organizations = boto3.client('organizations')

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
