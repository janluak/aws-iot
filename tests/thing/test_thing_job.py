from pathlib import Path
from pytest import mark, fail
from os import environ
import logging
import boto3
from uuid import uuid4
import json
import time

from aws_iot.thing import IoTJobThing


account_id = "None"
endpoint = "None"


class JobThing(IoTJobThing):
    def __init__(self):
        IoTJobThing.__init__(
            self,
            environ["TestThingName"],
            environ["AWS_REGION"],
            endpoint=endpoint,
            cert_path=Path(Path(__file__).parent, "../certs"),
        )

    def execute(self, job_document, job_id, version_number, execution_number):
        logging.warning(str(job_document))


@mark.skipif(condition='endpoint=="None"')
def test_two_consecutive_jobs(test_env, caplog):
    begin_ts = time.time()
    iot_client = boto3.client("iot", region_name=environ["AWS_REGION"])

    jt = JobThing()

    job_document1 = {"value": "1"}

    iot_client.create_job(
        jobId=str(uuid4()),
        targets=[
            f"arn:aws:iot:{environ['AWS_REGION']}:{account_id}:thing/{environ['TestThingName']}"
        ],
        document=json.dumps(job_document1),
    )

    while job_document1["value"] not in caplog.text:
        if time.time() > begin_ts + 18:
            fail("job wasn't executed")

    time.sleep(3)
    job_document2 = {"value": "2"}

    iot_client.create_job(
        jobId=str(uuid4()),
        targets=[
            f"arn:aws:iot:{environ['AWS_REGION']}:{account_id}:thing/{environ['TestThingName']}"
        ],
        document=json.dumps(job_document2),
    )

    while job_document2["value"] not in caplog.text:
        if time.time() > begin_ts + 18:
            fail("second job wasn't executed")

    jt.disconnect()
