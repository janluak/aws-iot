from os import environ
from boto3 import client


_client_data = {"region_name": environ["AWS_REGION"]}

if "IOT_ENDPOINT" in environ:
    _client_data.update({"endpoint_url": environ["IOT_ENDPOINT"]})

_iot_data_client = client("iot-data", **_client_data)
