import boto3
import botocore

BUCKET_NAME = 'a2s3pub' # replace with your bucket name


s3 = boto3.resource('s3')
def upload_file(name,dest):

# Upload a new file
    try:
        data = open(dest, 'rb')
        s3.Bucket(BUCKET_NAME).put_object(Key=name, Body=data)
    except botocore.exceptions.ClientError as e:
        if e.response['Error']['Code'] == "404":
            print("The object does not exist.")
        else:
            raise
def download_file(dest,name):
    try:
        s3.Bucket(BUCKET_NAME).download_file(name, dest)
    except botocore.exceptions.ClientError as e:
        if e.response['Error']['Code'] == "404":
            print("The object does not exist.")
        else:
            raise