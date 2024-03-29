from pathlib import Path
from pytest import fail, fixture
from os import environ
import logging
import boto3
from uuid import uuid4
import json
import time


TIMEOUT = 15

executed_job_ids = set()


def execute(job_document, job_id, version_number, execution_number):
    executed_job_ids.add(job_id)


def test_thing(test_env_real):
    from aws_iot.thing import ThingHandler

    begin_ts = time.time()
    iot_client = boto3.client("iot", region_name=environ["AWS_REGION"])

    t = ThingHandler(
        environ["TestThingName"],
        environ["AWS_REGION"],
        endpoint=environ["IOT_ENDPOINT"],
        cert_path=Path(Path(__file__).parent, "../certs"),
        delete_shadow_on_init=True,
        execution_function=execute,
    )

    job_id = str(uuid4())
    job_document = {"job_id": job_id}
    iot_client.create_job(
        jobId=job_id,
        targets=[
            f"arn:aws:iot:{environ['AWS_REGION']}:{environ['AWS_ACCOUNT_ID']}:thing/{environ['TestThingName']}"
        ],
        document=json.dumps(job_document),
    )

    t.shadow.reported = {"new_state": 1}
    assert t.shadow.reported == {"new_state": 1}
    assert t.shadow._full_state == {"reported": {"new_state": 1}}

    del t.shadow.reported
    assert t.shadow.reported == dict()

    while job_document["job_id"] not in executed_job_ids:
        if time.time() > begin_ts + TIMEOUT:
            fail("job wasn't executed")
    del t


def test_two_consecutive_jobs(test_env_real):
    from aws_iot.thing import ThingHandler

    begin_ts = time.time()
    iot_client = boto3.client("iot", region_name=environ["AWS_REGION"])

    t = ThingHandler(
        environ["TestThingName"],
        environ["AWS_REGION"],
        endpoint=environ["IOT_ENDPOINT"],
        cert_path=Path(Path(__file__).parent, "../certs"),
        delete_shadow_on_init=True,
    )
    t.execution_register(execute)

    job_document1 = {"job_id": str(uuid4())}

    iot_client.create_job(
        jobId=job_document1["job_id"],
        targets=[
            f"arn:aws:iot:{environ['AWS_REGION']}:{environ['AWS_ACCOUNT_ID']}:thing/{environ['TestThingName']}"
        ],
        document=json.dumps(job_document1),
    )

    while job_document1["job_id"] not in executed_job_ids:
        if time.time() > begin_ts + TIMEOUT:
            fail("job wasn't executed")

    time.sleep(3)
    job_document2 = {"job_id": str(uuid4())}

    iot_client.create_job(
        jobId=job_document2["job_id"],
        targets=[
            f"arn:aws:iot:{environ['AWS_REGION']}:{environ['AWS_ACCOUNT_ID']}:thing/{environ['TestThingName']}"
        ],
        document=json.dumps(job_document2),
    )
    begin_ts = time.time()

    while job_document2["job_id"] not in executed_job_ids:
        if time.time() > begin_ts + TIMEOUT:
            fail("job wasn't executed")
    del t
