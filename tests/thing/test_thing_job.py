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


@fixture
def job_thing_handler(iot_connector):
    from aws_iot.thing import ThingJobHandler

    def execute(job_document, job_id, version_number, execution_number):
        executed_job_ids.add(job_id)

    th = ThingJobHandler(aws_thing_connector=iot_connector)
    th.execution_register(execute)

    yield th
    th.thing.disconnect()


def test_execute_job(job_thing_handler):
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

    while job_document["job_id"] not in executed_job_ids:
        if time.time() > begin_ts + TIMEOUT:
            fail("job wasn't executed")


def test_two_consecutive_jobs(job_thing_handler):
    begin_ts = time.time()
    iot_client = boto3.client("iot", region_name=environ["AWS_REGION"])

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
            fail("second job wasn't executed")


def test_with_open_job_execute(iot_connector):
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

    from aws_iot.thing import ThingJobHandler

    def execute(job_document, job_id, version_number, execution_number):
        executed_job_ids.add(job_id)

    th = ThingJobHandler(aws_thing_connector=iot_connector)
    th.execution_register(execute, True)

    while job_document["job_id"] not in executed_job_ids:
        if time.time() > begin_ts + TIMEOUT:
            fail("job wasn't executed")


def test_with_open_job_skip_open(iot_connector):
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

    from aws_iot.thing import ThingJobHandler

    def execute(job_document, job_id, version_number, execution_number):
        executed_job_ids.add(job_id)

    ThingJobHandler(
        aws_thing_connector=iot_connector,
        execution_function=execute,
        execute_open_jobs_on_init=False,
    )

    while job_document["job_id"] not in executed_job_ids:
        if time.time() > begin_ts + TIMEOUT:
            return
    fail("job wasn't executed")


def test_context_of_connector_job_handler(test_env_real):
    from aws_iot.thing import IoTThingConnector

    begin_ts = time.time()
    iot_client = boto3.client("iot", region_name=environ["AWS_REGION"])

    with IoTThingConnector(
        environ["TestThingName"],
        environ["AWS_REGION"],
        endpoint=environ["IOT_ENDPOINT"],
        cert_path=Path(Path(__file__).parent, "../certs"),
    ) as connector:
        from aws_iot.thing import ThingJobHandler

        def execute(job_document, job_id, version_number, execution_number):
            executed_job_ids.add(job_id)

        th = ThingJobHandler(aws_thing_connector=connector)
        th.execution_register(execute)

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


def test_without_registered_execution(iot_connector):
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

    from src.aws_iot.thing import ThingJobHandler

    th = ThingJobHandler(
        aws_thing_connector=iot_connector,
    )

    while job_document["job_id"] not in executed_job_ids:
        if time.time() > begin_ts + TIMEOUT:
            break

    def execute(job_document, job_id, version_number, execution_number):
        executed_job_ids.add(job_id)

    th.execution_register(execute)
    begin_ts = time.time()

    while job_document["job_id"] not in executed_job_ids:
        if time.time() > begin_ts + TIMEOUT:
            fail("job wasn't executed")
