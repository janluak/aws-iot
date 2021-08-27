from pathlib import Path
from pytest import mark, fail
from os import environ
import logging
import boto3
from uuid import uuid4
import json
import time

from aws_iot.thing import IoTThing


account_id = "None"
endpoint = "None"


class Thing(IoTThing):
    def __init__(self):
        IoTThing.__init__(
            self,
            environ["TestThingName"],
            environ["AWS_REGION"],
            endpoint=endpoint,
            cert_path=Path(Path(__file__).parent, "../certs"),
            delete_shadow_on_init=True,
        )

    def handle_delta(self, *args):
        pass

    def execute(self, job_document, job_id, version_number, execution_number):
        logging.warning(str(job_document))


@mark.skipif(condition='endpoint=="None"')
def test_thing(test_env, caplog):
    begin_ts = time.time()
    iot_client = boto3.client("iot", region_name=environ["AWS_REGION"])

    t = Thing()

    job_value = str(uuid4())
    job_document = {"test": job_value}
    iot_client.create_job(
        jobId=job_value,
        targets=[
            f"arn:aws:iot:{environ['AWS_REGION']}:{account_id}:thing/{environ['TestThingName']}"
        ],
        document=json.dumps(job_document),
    )

    t.reported = {"new_state": 1}
    assert t.reported == {"new_state": 1}
    assert t._full_state == {"reported": {"new_state": 1}}

    del t.reported
    assert t.reported == dict()

    while job_value not in caplog.text:
        if time.time() > begin_ts + 25:
            fail("job wasn't executed")


@mark.skipif(condition='endpoint=="None"')
def test_two_consecutive_jobs(test_env, caplog):
    begin_ts = time.time()
    iot_client = boto3.client("iot", region_name=environ["AWS_REGION"])

    jt = Thing()

    job_document1 = {"value": str(uuid4())}

    iot_client.create_job(
        jobId=str(uuid4()),
        targets=[
            f"arn:aws:iot:{environ['AWS_REGION']}:{account_id}:thing/{environ['TestThingName']}"
        ],
        document=json.dumps(job_document1),
    )

    # import threading
    # threads = [i for i in threading.enumerate()]

    while job_document1["value"] not in caplog.text:
        if time.time() > begin_ts + 10:
            fail("job wasn't executed")

    time.sleep(3)
    job_document2 = {"value": str(uuid4())}

    iot_client.create_job(
        jobId=str(uuid4()),
        targets=[
            f"arn:aws:iot:{environ['AWS_REGION']}:{account_id}:thing/{environ['TestThingName']}"
        ],
        document=json.dumps(job_document2),
    )

    while job_document2["value"] not in caplog.text:
        if time.time() > begin_ts + 138:
            fail("job wasn't executed")
