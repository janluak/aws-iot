from .. import _BaseIoT
from os import environ
from boto3 import client
import json
from uuid import uuid4

__all__ = ["IoTJobHandler"]


_iot_client = client("iot", region_name=environ["AWS_REGION"])


class IoTJobHandler(_BaseIoT):
    def __init__(self, thing_name: str, account_id: str):
        super(IoTJobHandler, self).__init__(thing_name)
        self.__account_id = account_id

    def execute(self, job_document: dict, job_id: str = None):
        if self.__account_id is None:
            raise EnvironmentError("account id must be specified in order to execute")
        if not job_id:
            job_id = str(uuid4())
        return _iot_client.create_job(
            jobId=job_id,
            targets=[
                f"arn:aws:iot:{environ['AWS_REGION']}:{self.__account_id}:thing/{self.thing_name}"
            ],
            document=json.dumps(job_document),
        )
