from .shadow_handler import IoTShadowHandler
from .job_handler import IoTJobHandler


class IoTHandler:
    def __init__(
        self,
        thing_name: str,
        *,
        account_id: str = None,
        endpoint: str = None,
        region_name: str = None
    ):
        self.__job_handler = IoTJobHandler(thing_name, account_id, region_name)
        self.__shadow_handler = IoTShadowHandler(thing_name, endpoint, region_name)

    def execute(self, job_document: dict, job_id: str = None):
        self.__job_handler.execute(job_document, job_id)

    @property
    def shadow(self) -> IoTShadowHandler:
        return self.__shadow_handler
