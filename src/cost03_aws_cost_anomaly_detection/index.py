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

def lambda_handler(event, context):
    """AWS Lambda handler to check Cost Anomaly Detection monitor compliance."""
    logger.info("Starting Lambda handler execution")

    # Initialize AWS Config and Budgets clients
    logger.info("Initializing AWS clients")
    config = boto3.client('config')
    budgets = boto3.client('budgets')

    evaluations = []

    try:
        # Initialize Cost Explorer client (Cost Anomaly Detection is part of CE)
        logger.info("Initializing Cost Explorer client")
        ce = boto3.client('ce')

        try:
            # Get all anomaly monitors in the account
            logger.info("Retrieving anomaly monitors")
            response = ce.get_anomaly_monitors()

            # Check if any monitors exist
            monitor_count = len(response['AnomalyMonitors'])
            logger.info(f"Found {monitor_count} anomaly monitors")

            compliance_type = 'COMPLIANT' if monitor_count > 0 else 'NON_COMPLIANT'
            logger.info(f"Determined compliance status: {compliance_type}")

        except ce.exceptions.AccessDeniedException:
            logger.error("Access denied - ensure Lambda has ce:GetAnomalyMonitors permission")
            raise
        except Exception as e:
            logger.error(f"Error checking anomaly monitors: {str(e)}", exc_info=True)
            raise

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
        logger.error(f"Error evaluating compliance: {str(e)}", exc_info=True)
        raise
