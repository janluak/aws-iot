from os import environ
from boto3 import client


_iot_client = client("iot", region_name=environ["AWS_REGION"])
