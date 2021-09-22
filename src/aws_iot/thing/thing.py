from .connector import IoTThingConnector
from .shadow import ThingShadowHandler
from .job import ThingJobHandler
from abc import ABC, abstractmethod
from pathlib import Path


__all__ = ["ThingHandler"]


class ThingHandler(ABC):
    """
       Custom AWS thing taking care of the underlying functions used in AWS IoT
       """

    def __init__(
            self,
            thing_name: str = None,
            aws_region: str = None,
            endpoint: str = None,
            cert_path: (str, Path) = None,
            execute_open_jobs_on_init: bool = True,
            delete_shadow_on_init: bool = False,
    ):

        self.__connector = IoTThingConnector(thing_name, aws_region, endpoint, cert_path)
        self.__connector.connect()

        class ShadowHandler(ThingShadowHandler):
            def handle_delta(s, *args, **kwargs):
                self.handle_delta(*args, **kwargs)

        class JobHandler(ThingJobHandler):
            def execute(s, *args, **kwargs):
                self.execute(*args, **kwargs)

        self.__shadow_handler = ShadowHandler(
            delete_shadow_on_init=delete_shadow_on_init,
            aws_thing_connector=self.__connector
        )
        self.__job_handler = JobHandler(
            execute_open_jobs_on_init=execute_open_jobs_on_init,
            aws_thing_connector=self.__connector
        )

    @property
    def shadow(self) -> ThingShadowHandler:
        return self.__shadow_handler

    @property
    def job(self) -> ThingJobHandler:
        return self.__job_handler

    @abstractmethod
    def handle_delta(self, delta: dict, responseStatus: str, token: str):
        pass

    @abstractmethod
    def execute(self, job_document, job_id, version_number, execution_number):
        pass

    def __del__(self):
        self.__connector.disconnect()


