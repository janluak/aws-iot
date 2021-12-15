from .connector import IoTThingConnector
from .shadow import ThingShadowHandler
from .job import ThingJobHandler
from pathlib import Path
from typing import Callable


__all__ = ["ThingHandler"]


class ThingHandler:
    """
    Custom AWS thing taking care of the underlying functions used in AWS IoT
    """

    def __init__(
        self,
        thing_name: str = None,
        aws_region: str = None,
        endpoint: str = None,
        cert_path: (str, Path) = None,
        execution_function: Callable = None,
        execute_open_jobs_on_init: bool = True,
        delta_handler: Callable = None,
        delete_shadow_on_init: bool = False,
    ):

        self.__connector = IoTThingConnector(
            thing_name, aws_region, endpoint, cert_path
        )
        self.__connector.connect()

        self.__shadow_handler = ThingShadowHandler(
            delta_handler=delta_handler,
            delete_shadow_on_init=delete_shadow_on_init,
            aws_thing_connector=self.__connector,
        )
        self.__job_handler = ThingJobHandler(
            execution_function=execution_function,
            execute_open_jobs_on_init=execute_open_jobs_on_init,
            aws_thing_connector=self.__connector,
        )

    @property
    def thing(self) -> IoTThingConnector:
        return self.__connector

    @property
    def shadow(self) -> ThingShadowHandler:
        return self.__shadow_handler

    @property
    def job(self) -> ThingJobHandler:
        return self.__job_handler

    def delta_handler_register(self, func: Callable):
        self.shadow.delta_handler_register(func)

    def delta_handler_unregister(self):
        self.shadow.delta_handler_unregister()

    def execution_register(self, func: Callable, execute_open_jobs: bool = True):
        self.job.execution_register(func, execute_open_jobs)

    def execution_unregister(self):
        self.job.execution_unregister()

    def __del__(self):
        self.__connector.disconnect()
