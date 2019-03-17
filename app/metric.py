import boto3
import botocore
from datetime import datetime, timedelta
import os
from flask import render_template, session, request, redirect, url_for, g
import sys
client = boto3.client('cloudwatch')
command = 'wget -q -O - http://169.254.169.254/latest/meta-data/instance-id'
instance_id = os.popen(command)
response = client.put_metric_data(
    Namespace='http_request',
    MetricData=[
        {
            'MetricName': 'http',
            'Dimensions': [
                {
                    'Name': 'InstanceId',
                    'Value': instance_id
                },
            ],
            'Timestamp': datetime.now(),
            'Value': session['request'],
            'StatisticValues': {
                'SampleCount': 200,
                'Sum': 300,
                'Minimum': 12.0,
                'Maximum': 123.0
            },
            'Values': [
                session['request']
            ],
            'Counts': [
                60
            ],
            'Unit': 'Count/Minute',
            'StorageResolution': 60
        },
    ]
)