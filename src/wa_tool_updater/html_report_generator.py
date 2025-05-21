"""
HTML Report Generator for Well-Architected Conformance Data

This module generates an HTML report from AWS Config compliance data
using Jinja2 templating and uploads it to an S3 bucket.
"""

import boto3
import logging
import datetime
import os
from typing import Dict, Any
from jinja2 import Environment, FileSystemLoader, select_autoescape

logger = logging.getLogger()

def generate_html_report(compliance_data: Dict[str, Any], account_id: str, region: str) -> str:
    """
    Generate HTML report from compliance data using Jinja2 templating
    
    Args:
        compliance_data: Dictionary containing compliance data by pillar and best practice
        account_id: AWS Account ID
        region: AWS Region
    
    Returns:
        HTML content as string
    """
    # Setup Jinja2 environment
    template_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'templates')
    env = Environment(
        loader=FileSystemLoader(template_dir),
        autoescape=select_autoescape(['html', 'xml'])
    )
    
    # Get the template
    template = env.get_template('report_template.html')
    
    # Render the template with our data
    html_content = template.render(
        compliance_data=compliance_data,
        account_id=account_id,
        region=region,
        generation_time=datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S UTC")
    )
    
    return html_content


def upload_report_to_s3(html_content: str, bucket_name: str) -> str:
    """
    Upload HTML report to S3 bucket
    
    Args:
        html_content: HTML content to upload
        bucket_name: S3 bucket name
    
    Returns:
        S3 URL of the uploaded report
    """
    if not bucket_name:
        logger.warning("No S3 bucket name provided, skipping report upload")
        return ""
        
    s3_client = boto3.client('s3')
    
    # Generate filename with timestamp
    timestamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    filename = f"Reports/well_architected_compliance_report_{timestamp}.html"
    
    try:
        s3_client.put_object(
            Bucket=bucket_name,
            Key=filename,
            Body=html_content,
            ContentType='text/html'
        )
        logger.info(f"Successfully uploaded report to s3://{bucket_name}/{filename}")
        return f"s3://{bucket_name}/{filename}"
    except Exception as e:
        logger.error(f"Error uploading report to S3: {str(e)}")
        return ""
