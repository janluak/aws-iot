from aws_iot.thing import (
    ThingHandler,
    IoTThingConnector,
    ThingShadowHandler,
    ThingJobHandler,
)
from aws_iot.base_shadow import BaseShadow
from aws_iot.thing.shadow import (
    _update_nested_dict,
    _delete_values_if_present,
    _delete_keys_if_values_equal,
)
from unittest.mock import MagicMock
from AWSIoTPythonSDK.MQTTLib import AWSIoTMQTTClient
from pathlib import Path
from typing import Callable
from copy import deepcopy
import inspect


__all__ = ["MockConnector", "MockThingHandler", "MockShadowHandler", "MockJobHandler"]


class MockMQTT(AWSIoTMQTTClient):
    def __init__(self):
        for i in self.__dir__():
            if not i.startswith("_") and i != "reset_mock":
                self.__setattr__(i, MagicMock())

    def reset_mock(self):
        for i in self.__dir__():
            if isinstance(self.__getattribute__(i), MagicMock):
                self.__getattribute__(i).reset_mock()


class MockConnector(IoTThingConnector):
    publish = MagicMock()

    def __init__(self, thing_name: str, **_):
        self.__thing_name = thing_name
        self.__mqtt_client = MockMQTT()
        self.__connected = True

    @property
    def thing_name(self) -> str:
        return self.__thing_name

    @property
    def mqtt(self) -> AWSIoTMQTTClient:
        return self.__mqtt_client

    @property
    def connected(self) -> bool:
        return self.__connected

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.disconnect()

    def reset_mock(self):
        self.mqtt.reset_mock()
        for i in self.__dir__():
            if isinstance(self.__getattribute__(i), MagicMock):
                self.__getattribute__(i).reset_mock()


class MockJobHandler(ThingJobHandler):
    def __init__(
        self,
        thing_name: str = None,
        aws_region: str = None,
        endpoint: str = None,
        cert_path: (str, Path) = None,
        execution_function: Callable = None,
        execute_open_jobs_on_init: bool = True,
        aws_thing_connector: IoTThingConnector = None,
    ):
        self.__execution = None
        if aws_thing_connector:
            self.__thing_connector = aws_thing_connector
        else:
            self.__thing_connector = MockConnector(
                thing_name,
                aws_region=aws_region,
                endpoint=endpoint,
                cert_path=cert_path,
            )
            self.__thing_connector.connect()

        self.__jobs_done = True
        self.__jobs_started = int()
        self.__jobs_succeeded = int()
        self.__jobs_rejected = int()

        if execution_function:
            self.execution_register(execution_function, execute_open_jobs_on_init)

    @property
    def thing(self):
        return self.__thing_connector

    @property
    def jobs_done(self):
        return self.__jobs_done

    @property
    def job_stats(self):
        return {
            "jobsStarted": self.__jobs_started,
            "jobsSucceeded": self.__jobs_succeeded,
            "jobsRejected": self.__jobs_rejected,
        }

    def execution_register(self, func: Callable, execute_open_jobs: bool = True):
        s = inspect.signature(func).parameters
        if len(s.items()) < 1:
            raise TypeError(
                "execution_handler function must at least accept one argument"
            )
        elif len(s.items()) > 4:
            raise TypeError(
                "execution_handler function must not accept more than four arguments"
            )
        self.__execution = func

    def execution_unregister(self):
        self.__remove_job_subscription()
        self.__execution = None

    def reset_mock(self):
        for i in self.__dir__():
            if i.startswith(f"_{self.__class__.__base__}"):
                continue
            if isinstance(self.__getattribute__(i), MagicMock):
                self.__getattribute__(i).reset_mock()


class MockShadowHandler(ThingShadowHandler):
    def __init__(
        self,
        thing_name: str = None,
        aws_region: str = None,
        endpoint: str = None,
        cert_path: (str, Path) = None,
        delta_handler: Callable = None,
        delete_shadow_on_init: bool = False,
        aws_thing_connector: IoTThingConnector = None,
    ):
        self.__delta_handler = (
            delta_handler if delta_handler else self._default_delta_handler
        )
        if aws_thing_connector:
            self.__thing_connector = aws_thing_connector
        else:
            self.__thing_connector = MockConnector(
                thing_name,
                aws_region=aws_region,
                endpoint=endpoint,
                cert_path=cert_path,
            )
            self.__thing_connector.connect()

        BaseShadow.__init__(self)
        self.__delete_shadow_on_init = delete_shadow_on_init

        self.__cache_new_state = dict()

    @property
    def thing(self):
        return self.__thing_connector

    @property
    def state(self) -> dict:
        return self._full_state

    @state.setter
    def state(self, new_state: dict):
        self.reported = new_state

    @state.deleter
    def state(self):
        del self.reported

    @property
    def desired(self) -> dict:
        return self._full_state.get("state", dict()).get("desired", dict())

    @property
    def reported(self) -> dict:
        return self._full_state.get("state", dict()).get("reported", dict())

    @reported.setter
    def reported(self, new_state: dict):
        if not isinstance(new_state, dict):
            raise TypeError(
                f"new reported state must be of type dict, provided {type(new_state)}"
            )
        self.update_shadow(new_state)

    @reported.deleter
    def reported(self):
        self._full_state.update({"state": {"reported": None}})

    @property
    def delta(self) -> dict:
        return self._full_state.get("state", dict()).get("delta", dict())

    def _default_delta_handler(self, delta: dict, responseStatus: str, token: str):
        self.update_shadow(delta)

    def update_shadow(
        self, new_state: (dict, None) = None, clear_desired: bool = False
    ):
        state = deepcopy(self._full_state.get("reported", dict()))

        if new_state:
            state.update(new_state)
        if self.__cache_new_state:
            state = _update_nested_dict(state, self.__cache_new_state)
            self.__cache_new_state = dict()

        update_state = {
            "state": {
                "reported": _delete_values_if_present(
                    state, self._full_state.get("reported", dict())
                )
            }
        }
        if clear_desired:
            update_state["state"]["desired"] = _delete_values_if_present(
                self.desired, new_state, True
            )

        update_state = _delete_keys_if_values_equal(
            update_state,
            {
                "state": {
                    "reported": self._full_state.get("reported", dict()),
                    "desired": self._full_state.get("desired", dict()),
                }
            },
        )
        self._full_state.update(update_state)

    def delete_shadow(self) -> None:
        self._full_state = dict()

    def reset_mock(self):
        for i in self.__dir__():
            if isinstance(self.__getattribute__(i), MagicMock):
                self.__getattribute__(i).reset_mock()


class MockThingHandler(ThingHandler):
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

        self.__connector = MockConnector(
            thing_name, aws_region=aws_region, endpoint=endpoint, cert_path=cert_path
        )
        self.__connector.connect()

        self.__shadow_handler = MockShadowHandler(
            delta_handler=delta_handler,
            delete_shadow_on_init=delete_shadow_on_init,
            aws_thing_connector=self.__connector,
        )

        self.__job_handler = MockJobHandler(
            execution_function=execution_function,
            execute_open_jobs_on_init=execute_open_jobs_on_init,
            aws_thing_connector=self.__connector,
        )

        self.delta_handler_register = MagicMock(
            return_value=self.shadow.delta_handler_register
        )
        self.delta_handler_unregister = MagicMock(
            return_value=self.shadow.delta_handler_unregister
        )
        self.execution_register = MagicMock(return_value=self.job.execution_register)
        self.execution_unregister = MagicMock(
            return_value=self.job.execution_unregister
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

    def reset_mock(self):
        self.thing.reset_mock()
        self.shadow.reset_mock()
        self.job.reset_mock()
        self.delta_handler_register.reset_mock()
        self.delta_handler_unregister.reset_mock()
        self.execution_register.reset_mock()
        self.execution_unregister.reset_mock()

    def __del__(self):
        pass
