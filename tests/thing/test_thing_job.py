from pathlib import Path
from pytest import mark, fail
from os import environ
import logging
import boto3
from uuid import uuid4
import json
import time

from aws_iot.thing import IoTJobThing


account_id = "876169258212"
endpoint = "at7c82lz6730l"


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

    job_document1 = {"test": "1"}

    iot_client.create_job(
        jobId=str(uuid4()),
        targets=[
            f"arn:aws:iot:{environ['AWS_REGION']}:{account_id}:thing/{environ['TestThingName']}"
        ],
        document=json.dumps(job_document1),
    )

    while len(caplog.messages) == 0:
        if time.time() > begin_ts + 10:
            fail("job wasn't executed")

    time.sleep(3)
    job_document2 = {"test": "2"}

    iot_client.create_job(
        jobId=str(uuid4()),
        targets=[
            f"arn:aws:iot:{environ['AWS_REGION']}:{account_id}:thing/{environ['TestThingName']}"
        ],
        document=json.dumps(job_document2),
    )

    while len(caplog.messages) == 1:
        if time.time() > begin_ts + 15:
            fail("job wasn't executed")

    jt.disconnect()

    if str(job_document1) not in caplog.text:
        fail("job wasn't executed")
    if str(job_document2) not in caplog.text:
        fail("second job not executed")