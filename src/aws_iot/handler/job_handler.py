from os import environ
import json
from uuid import uuid4

__all__ = ["IoTJobHandler"]


class IoTJobHandler:
    def __init__(
        self,
        thing_name: str,
        account_id: str = None,
        region_name: str = None,
        client=None,
    ):
        self.__thing_name = thing_name
        self.__region_name = (
            environ["AWS_REGION"] if region_name is None else region_name
        )
        try:
            self.__account_id = (
                environ["AWS_ACCOUNT_ID"] if account_id is None else account_id
            )
        except KeyError:
            raise ValueError(
                "missing account id:\n"
                "for using IoTJobHandler account id must either be given as argument or "
                "defined in os.environ as AWS_ACCOUNT_ID"
            )

        if client:
            self.__client = client
        else:
            from ._iot_client import _iot_client

            self.__client = _iot_client

    @property
    def thing_name(self) -> str:
        return self.__thing_name

    @property
    def region_name(self) -> str:
        return self.__region_name

    def execute(self, job_document: dict, job_id: str = None):
        if not job_id:
            job_id = str(uuid4())
        return self.__client.create_job(
            jobId=job_id,
            targets=[
                f"arn:aws:iot:{self.__region_name}:{self.__account_id}:thing/{self.thing_name}"
            ],
            document=json.dumps(job_document),
        )
