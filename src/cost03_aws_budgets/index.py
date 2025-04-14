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
    try:
        account_id = event['accountId']
        logger.info(f"Checking budget compliance for account: {account_id}")

        # Get all budgets in the account
        response = budgets.describe_budgets(AccountId=account_id)

        # First check if any budgets exist
        if not response['Budgets']:
            logger.warning(f"No budgets found for account: {account_id}")
            return 'NON_COMPLIANT'

        logger.info(f"Found {len(response['Budgets'])} budgets")

        # For each budget, check if it has notifications with email subscribers
        has_email_notification = False

        for budget in response['Budgets']:
            budget_name = budget['BudgetName']
            logger.info(f"Checking notifications for budget: {budget_name}")

            # Get notifications for this budget
            notifications = budgets.describe_notifications_for_budget(
                AccountId=account_id,
                BudgetName=budget_name
            )

            notification_count = len(notifications.get('Notifications', []))
            logger.info(f"Found {notification_count} notifications for budget: {budget_name}")

            if notification_count > 0:
                # Check subscribers for each notification
                for notification in notifications['Notifications']:
                    subscribers = budgets.describe_subscribers_for_notification(
                        AccountId=account_id,
                        BudgetName=budget_name,
                        Notification=notification
                    )

                    if any(sub['SubscriptionType'] == 'EMAIL'
                          for sub in subscribers.get('Subscribers', [])):
                        logger.info(f"Found email notification in budget: {budget_name}")
                        has_email_notification = True
                        break

            if has_email_notification:
                break

        compliance_type = 'COMPLIANT' if has_email_notification else 'NON_COMPLIANT'
        logger.info(f"Budget compliance status: {compliance_type}")
        return compliance_type

    except Exception as e:
        logger.error(f"Error in check_budget_compliance: {str(e)}", exc_info=True)
        raise


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
