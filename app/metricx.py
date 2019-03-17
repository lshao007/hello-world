import boto3
import sys
from datetime import datetime, timedelta,date,time
import matplotlib.pyplot as plt

import os

def fun():
    try:
        if session['request'] > 1:

    except:
        session['request']=1
    return session['request']

def oploadrequest(request):
    command = 'wget -q -O - http://169.254.169.254/latest/meta-data/instance-id'
    instance_id = os.popen(command)
    cnx = get_db()
    cursor = cnx.cursor()
    query = "INSERT INTO requests (rate,instance_id) VALUES (%s,%s)"
    cursor.execute(query, (request,instance_id))
    cursor.close()
    cnx.commit()

def runTask(day=0, hour=0, min=0, second=0):
    # Init time
    now = datetime.now()
    strnow = now.strftime('%Y-%m-%d %H:%M:%S')
    # First next run time
    period = timedelta(days=day, hours=hour, minutes=min, seconds=second)
    next_time = now + period
    strnext_time = next_time.strftime('%Y-%m-%d %H:%M:%S')
    while True:
        # Get system current time
        iter_now = datetime.now()
        iter_now_time = iter_now.strftime('%Y-%m-%d %H:%M:%S')
        if str(iter_now_time) == str(strnext_time):
            # Get every start work time
            # Call task func
            fun()
            # Get next iteration time
            iter_time = iter_now + period
            strnext_time = iter_time.strftime('%Y-%m-%d %H:%M:%S')
            continue

# runTask(work, min=0.5)
runTask(day=0, hour=0, min=1,second=0)

