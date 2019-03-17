import boto3
import botocore
from datetime import datetime, timedelta
import os
from flask import render_template, session, request, redirect, url_for, g
import sys
client = boto3.client('cloudwatch')
command = 'wget -q -O - http://169.254.169.254/latest/meta-data/instance-id'
instance_id = os.popen(command)
def start():
    try:
     session['request']
     value=session['request']
    except:
        value=1
    return value
value=start()
response = client.put_metric_data(
    Namespace='http_request',
    MetricData=[
        {
            'MetricName': 'http',
            'Dimensions': [
                {
                    'Name': 'InstanceId',
                    'Value':instance_id
                },
            ],
            'Timestamp': datetime.now(),
            'Value': value,
            'Unit': 'Count/Second',
            'StorageResolution': 60
        },
    ]
)