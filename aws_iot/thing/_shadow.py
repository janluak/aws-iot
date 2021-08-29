from ._base import _BaseIoTThing, MQTT_OPERATION_TIMEOUT
from .._base_shadow import _BaseShadow
from AWSIoTPythonSDK.MQTTLib import AWSIoTMQTTShadowClient
from AWSIoTPythonSDK.core.shadow.deviceShadow import deviceShadow
from abc import abstractmethod, ABC
from threading import Lock
from pathlib import Path
import json
import logging
from copy import deepcopy
from time import sleep
import inspect
from collections import Mapping


__all__ = ["IoTShadowThing"]


def _is_parent_function(parent_func_name: str) -> bool:
    """
    Returns the name of the parent function calling

    Parameters
    ----------
    parent_func_name : str
        the name of the parent function to check if equal to

    Returns
    -------
    str

    """
    return inspect.stack()[2].function == parent_func_name


def _update_nested_dict(original_dict, new_values):
    for k, v in new_values.items():
        if isinstance(v, Mapping):
            original_dict[k] = _update_nested_dict(original_dict.get(k, {}), v)
        else:
            original_dict[k] = v
    return original_dict


def _delete_values_if_present(
    origin: dict, compare: dict, set_value_to_None: bool = False
) -> dict:
    """
    Delete all key-value-pairs in origin if value present in `compare`

    Parameters
    ----------
    origin : dict
        the original dictionary to delete keys if values equally present in `compare`
    compare : dict
        the dictionary to compare the origin to

    Returns
    -------
    origin : dict
        the original dictionary without the duplicated keys

    """

    def delete(d, k):
        del d[k]

    def set_to_none(d, k):
        d[k] = None

    change = {False: delete, True: set_to_none}[set_value_to_None]

    for key in origin.copy():
        if key not in compare:
            continue
        if isinstance(origin[key], dict):
            origin[key] = _delete_values_if_present(origin[key], compare[key])
            if not origin[key]:
                change(origin, key)
        elif compare[key] == origin[key]:
            change(origin, key)

    return origin


def _update_state_from_response(reported_state, response):
    if response is None:
        return dict()

    for key, value in response.items():
        if value is None:
            reported_state.pop(key, 0)
        # elif isinstance(value, list):
        #     for item_no in range(len(value)):
        #         value[item_no] =
        elif isinstance(value, dict):
            try:
                reported_state[key] = _update_state_from_response(
                    reported_state[key], response[key]
                )
            except KeyError:
                reported_state[key] = value
        else:
            reported_state[key] = value

    return reported_state


class IoTShadowThing(_BaseIoTThing, _BaseShadow, ABC):
    """
    Custom AWS thing shadow taking care of the underlying functions used in AWS shadows
    """

    def __init__(
        self,
        thing_name: str,
        aws_region: str,
        endpoint: str,
        cert_path: (str, Path) = None,
        delete_shadow_on_init: bool = False,
    ):
        """
        Parameters
        ----------
        thing_name : str
            the name of the AWS thing
            needs to be identical to the name of an AWS thing as configured in the management console
        aws_region : str
            region of AWS thing management
        endpoint : str
            MQTT enpoint of the desired AWS account
        cert_path : str, Path
            directory of the certificates
        delete_shadow_on_init : bool
            if True: shadow is deleted on every new instantiation

        """
        _BaseIoTThing.__init__(self, thing_name, aws_region, endpoint, cert_path)
        _BaseShadow.__init__(self)
        self.__delete_shadow_on_init = delete_shadow_on_init

        self.__cache_new_state = dict()

        self.__update_lock = Lock()
        self.__get_shadow_lock = Lock()

        self.__create_aws_mqtt_shadow_client()
        self.__create_aws_handler()

        if not delete_shadow_on_init:
            self.__get_shadow()
        # self.log.success("finished initialization of object " + self.__class__.__name__)

    def __create_aws_mqtt_shadow_client(self):
        """
        Initializes the AWSIoTMQTTShadowClient mqtt broker

        """
        self.__shadow_client = AWSIoTMQTTShadowClient(
            self.thing_name, awsIoTMQTTClient=self.mqtt
        )

    def __create_aws_handler(self):
        """
        Create the handler for the AWS IoT shadow handler
        """

        self.__shadow_handler = self._shadow_client.createShadowHandlerWithName(
            shadowName=self.thing_name, isPersistentSubscribe=True
        )

        if _is_parent_function("__init__") and self.__delete_shadow_on_init:
            self.delete_shadow()
            self.update_shadow(dict())

        self._shadow_handler.shadowRegisterDeltaCallback(self.__parse_delta)

    def __wait_for_possible_updates_finished(self):
        while self.__update_lock.locked():
            pass

    @property
    def state(self) -> dict:
        self.__wait_for_possible_updates_finished()
        return super().state

    @state.setter
    def state(self, new_state: dict):
        self.reported = new_state

    @state.deleter
    def state(self):
        del self.reported

    @property
    def reported(self) -> dict:
        self.__wait_for_possible_updates_finished()
        return super().reported

    @reported.setter
    def reported(self, new_state: dict):
        if not isinstance(new_state, dict):
            raise TypeError(
                f"new reported state must be of type dict, provided {type(new_state)}"
            )

        self.update_shadow(new_state)

    @reported.deleter
    def reported(self):
        self.__update_lock.acquire()
        self._shadow_handler.shadowUpdate(
            json.dumps({"state": {"reported": None}}),
            self.__callback_updating_shadow,
            MQTT_OPERATION_TIMEOUT,
        )

    @abstractmethod
    def handle_delta(self, delta: dict, responseStatus: str, token: str):
        pass

    def __parse_delta(self, payload, responseStatus, token):
        payload = json.loads(payload)
        self._version = payload["version"]
        self._update_timestamp = payload["timestamp"]
        if not self.desired:
            self._full_state["desired"] = dict()
        self._full_state["desired"].update(payload["state"])
        self.handle_delta(payload["state"], responseStatus, token)

    def cache_new_state(self, new_state: dict):
        self.__cache_new_state = _update_nested_dict(self.__cache_new_state, new_state)

    def update_shadow(
        self, new_state: (dict, None) = None, clear_desired: bool = False
    ):
        self.__update_lock.acquire()
        state = deepcopy(self._full_state.get("reported", dict()))

        if new_state:
            state.update(new_state)
        if self.__cache_new_state:
            state = _update_nested_dict(state, self.__cache_new_state)
            self.__cache_new_state = dict()

        update_state = {
            "state": {
                "reported": _delete_values_if_present(state, self._full_state.get("reported", dict()))
            }
        }
        if clear_desired:
            update_state["state"]["desired"] = _delete_values_if_present(
                self.desired, new_state, True
            )

        if update_state != {
            "state": {
                "reported": self._full_state.get("reported", dict()),
                "desired": self._full_state.get("desired", dict())
            }
        }:
            self._shadow_handler.shadowUpdate(
                json.dumps(update_state),
                self.__callback_updating_shadow,
                MQTT_OPERATION_TIMEOUT,
            )

    def __callback_get_shadow(self, *args):
        if args[1] == "accepted":
            payload = json.loads(args[0])
            self._full_state = payload["state"]
            self._meta = payload["metadata"]
            self._version = payload["version"]
            self._update_timestamp = payload["timestamp"]
        else:
            logging.critical(f"__callback_get_shadow: not parsed response: {args}")
        self.__get_shadow_lock.release()

    def _get_property_of_state(self, prop):
        while self.__get_shadow_lock.locked():
            sleep(0.1)
        return deepcopy(self._full_state.get(prop, dict()))

    def __get_shadow(self):
        self.__get_shadow_lock.acquire()
        self._shadow_handler.shadowGet(
            self.__callback_get_shadow, MQTT_OPERATION_TIMEOUT
        )

    def delete_shadow(self) -> None:
        self._shadow_handler.shadowDelete(
            self.__callback_deleting_shadow, MQTT_OPERATION_TIMEOUT
        )

    @property
    def _shadow_client(self) -> AWSIoTMQTTShadowClient:
        return self.__shadow_client

    @property
    def _shadow_handler(self) -> deviceShadow:
        return self.__shadow_handler

    def __callback_updating_shadow(self, payload, responseStatus, token):
        if responseStatus == "accepted":
            payload = json.loads(payload)
            self._full_state["reported"] = _update_state_from_response(
                self._get_property_of_state("reported"), payload["state"]["reported"]
            )
            logging.info("successfully updated shadow file")
        else:
            logging.critical(
                f"__callback_updating_shadow: not parsed response: {payload}"
            )

        self.__update_lock.release()
        if "delta" in responseStatus:
            self.__parse_delta(payload, responseStatus, token)

    def __callback_deleting_shadow(self, *args):
        """
        Callback Function: telling whether the tried cleaning of the shadow was successful

        Parameters
        ----------
        args
            if [1] `accepted`, cleaning was correct
            elif [0]["code"] == 404: no file available to clean

        """
        if args[1] == "accepted":
            logging.info("successfully cleaned shadow file")
            self._full_state = dict()
        else:
            try:
                status_code = json.loads(args[0])["code"]
                if status_code == 404:
                    logging.warning("no shadow file for cleaning available")
            except KeyError:
                logging.error(
                    "something went wrong with cleaning the shadow file. Response from AWS: "
                    + str(args)
                )
