from pathlib import Path
from pytest import fail, fixture
from os import environ
import logging
import boto3
from uuid import uuid4
import json
import time


TIMEOUT = 10

executed_job_ids = set()


@fixture
def job_thing_handler():
    from aws_iot.thing import ThingJobHandler

    class JobThing(ThingJobHandler):
        def execute(self, job_document, job_id, version_number, execution_number):
            executed_job_ids.add(job_id)

    yield JobThing


def test_execute_job(mqtt_connection, job_thing_handler):
    begin_ts = time.time()
    iot_client = boto3.client("iot", region_name=environ["AWS_REGION"])

    jt = job_thing_handler(
        aws_thing_connector=mqtt_connection,
    )

    job_document = {"job_id": str(uuid4())}

    iot_client.create_job(
        jobId=job_document["job_id"],
        targets=[
            f"arn:aws:iot:{environ['AWS_REGION']}:{environ['AWS_ACCOUNT_ID']}:thing/{environ['TestThingName']}"
        ],
        document=json.dumps(job_document),
    )

    while job_document["job_id"] not in executed_job_ids:
        if time.time() > begin_ts + TIMEOUT:
            fail("job wasn't executed")
    jt.thing.disconnect()


def test_two_consecutive_jobs(mqtt_connection, job_thing_handler):
    begin_ts = time.time()
    iot_client = boto3.client("iot", region_name=environ["AWS_REGION"])

    job_thing_handler(
        aws_thing_connector=mqtt_connection,
    )

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

    while job_document2["job_id"] not in executed_job_ids:
        if time.time() > begin_ts + TIMEOUT:
            fail("second job wasn't executed")


def test_with_open_job_execute(mqtt_connection, job_thing_handler):
    begin_ts = time.time()
    iot_client = boto3.client("iot", region_name=environ["AWS_REGION"])

    job_document = {"job_id": str(uuid4())}

    iot_client.create_job(
        jobId=job_document["job_id"],
        targets=[
            f"arn:aws:iot:{environ['AWS_REGION']}:{environ['AWS_ACCOUNT_ID']}:thing/{environ['TestThingName']}"
        ],
        document=json.dumps(job_document),
    )

    time.sleep(3)

    job_thing_handler(
        aws_thing_connector=mqtt_connection,
    )

    while job_document["job_id"] not in executed_job_ids:
        if time.time() > begin_ts + TIMEOUT:
            fail("job wasn't executed")


def test_with_open_job_skip_open(mqtt_connection, job_thing_handler):
    begin_ts = time.time()
    iot_client = boto3.client("iot", region_name=environ["AWS_REGION"])

    job_document = {"job_id": str(uuid4())}

    iot_client.create_job(
        jobId=job_document["job_id"],
        targets=[
            f"arn:aws:iot:{environ['AWS_REGION']}:{environ['AWS_ACCOUNT_ID']}:thing/{environ['TestThingName']}"
        ],
        document=json.dumps(job_document),
    )

    time.sleep(3)

    job_thing_handler(
        aws_thing_connector=mqtt_connection,
        execute_open_jobs_on_init=False
    )

    while job_document["job_id"] not in executed_job_ids:
        if time.time() > begin_ts + TIMEOUT:
            return
    fail("job wasn't executed")


def test_context_of_connector_job_handler(test_env_real, job_thing_handler):
    from aws_iot.thing import IoTThingConnector
    begin_ts = time.time()
    iot_client = boto3.client("iot", region_name=environ["AWS_REGION"])

    with IoTThingConnector(
            environ["TestThingName"],
            environ["AWS_REGION"],
            endpoint=environ["IOT_ENDPOINT"],
            cert_path=Path(Path(__file__).parent, "../certs")
    ) as connector:
        job_thing_handler(
            aws_thing_connector=connector
        )

        job_document = {"job_id": str(uuid4())}

        iot_client.create_job(
            jobId=job_document["job_id"],
            targets=[
                f"arn:aws:iot:{environ['AWS_REGION']}:{environ['AWS_ACCOUNT_ID']}:thing/{environ['TestThingName']}"
            ],
            document=json.dumps(job_document),
        )

        while job_document["job_id"] not in executed_job_ids:
            if time.time() > begin_ts + TIMEOUT:
                fail("job wasn't executed")
