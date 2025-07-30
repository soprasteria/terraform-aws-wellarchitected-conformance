import boto3
import logging
from datetime import datetime

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Create a formatter
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')

# Initialize AWS Config and Budgets clients
logger.info("Initializing AWS clients")
config = boto3.client('config')
budgets = boto3.client('budgets')

def check_budget_compliance(budgets, event):
    """Check if budgets exist and have email notifications configured."""
    account_id = event['accountId']

    for budget in budgets.describe_budgets(AccountId=account_id).get('Budgets', []):
        for notification in budgets.describe_notifications_for_budget(
            AccountId=account_id, BudgetName=budget['BudgetName']
        ).get('Notifications', []):
            if any(sub['SubscriptionType'] == 'EMAIL' for sub in
                   budgets.describe_subscribers_for_notification(
                       AccountId=account_id,
                       BudgetName=budget['BudgetName'],
                       Notification=notification
                   ).get('Subscribers', [])):
                return 'COMPLIANT'

    return 'NON_COMPLIANT'


def lambda_handler(event, context):
    """AWS Lambda handler function."""
    logger.info("Starting Lambda handler execution")

    try:

        evaluations = []

        # Get compliance status
        compliance_type = check_budget_compliance(budgets, event)

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
