from moto import mock_iot
from boto3 import client
from os import environ
import json


@mock_iot
def test_execute_job(setup_thing):
    iot_client = client("iot", region_name=environ["AWS_REGION"])
    from aws_iot.handler import IoTJobHandler

    job_document = {"test": "document"}
    resp = IoTJobHandler(environ["TestThingName"], environ["AWS_ACCOUNT_ID"]).execute(
        job_document
    )

    jobs = iot_client.list_jobs()["jobs"]
    assert any(resp["jobArn"] in i["jobArn"] for i in jobs)
    assert (
        json.loads(iot_client.get_job_document(jobId=resp["jobId"])["document"])
        == job_document
    )
