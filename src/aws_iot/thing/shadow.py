from .connector import IoTThingConnector, MQTT_OPERATION_TIMEOUT
from ..base_shadow import BaseShadow
from AWSIoTPythonSDK.MQTTLib import AWSIoTMQTTShadowClient
from typing import Callable
from threading import Lock
from pathlib import Path
import json
import logging
from copy import deepcopy
from time import sleep
import inspect
from collections import Mapping


__all__ = ["ThingShadowHandler"]


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


def _delete_keys_if_values_equal(origin: dict, compare: dict) -> dict:
    for key in origin.copy():
        if isinstance(origin[key], dict) and key in compare:
            origin[key] = _delete_values_if_present(origin[key], compare[key])
        elif isinstance(origin[key], list):
            for index, value in origin[key]:
                origin[key][index] = (
                    _delete_values_if_present(origin[key][index], compare[key][index])
                    if len(compare[key]) > index
                    else origin[key][index]
                )
        else:
            if origin[key] == compare[key]:
                del origin[key]
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


class ThingShadowHandler(BaseShadow):
    """
    Custom AWS thing shadow taking care of the underlying functions used in AWS shadows
    """

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
        delta_handler: Callable
            function handling any delta updates from AWS cloud shadow
        delete_shadow_on_init : bool
            if True: shadow is deleted on every new instantiation
        aws_thing_connector : IoTThingConnector
            mqtt connection handler to AWS

        """
        self.__delta_handler = (
            delta_handler if delta_handler else self._default_delta_handler
        )
        if aws_thing_connector:
            self.__thing_connector = aws_thing_connector
        else:
            self.__thing_connector = IoTThingConnector(
                thing_name, aws_region, endpoint, cert_path
            )
            self.__thing_connector.connect()

        BaseShadow.__init__(self)
        self.__delete_shadow_on_init = delete_shadow_on_init

        self.__cache_new_state = dict()

        self.__update_lock = Lock()
        self.__get_shadow_lock = Lock()

        self.__create_aws_mqtt_shadow_client()
        self.__create_aws_handler()

        if not delete_shadow_on_init:
            self.__get_shadow()
        # self.log.success("finished initialization of object " + self.__class__.__name__)

    @property
    def thing(self):
        return self.__thing_connector

    def __create_aws_mqtt_shadow_client(self):
        """
        Initializes the AWSIoTMQTTShadowClient mqtt broker

        """
        self.__shadow_client = AWSIoTMQTTShadowClient(
            self.thing.thing_name, awsIoTMQTTClient=self.thing.mqtt
        )

    def __create_aws_handler(self):
        """
        Create the handler for the AWS IoT shadow handler
        """

        self.__shadow_handler = self.__shadow_client.createShadowHandlerWithName(
            shadowName=self.thing.thing_name, isPersistentSubscribe=True
        )

        if _is_parent_function("__init__") and self.__delete_shadow_on_init:
            self.delete_shadow()
            self.update_shadow(dict())

        self.__shadow_handler.shadowRegisterDeltaCallback(self.__parse_delta)

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
        self.__shadow_handler.shadowUpdate(
            json.dumps({"state": {"reported": None}}),
            self.__callback_updating_shadow,
            MQTT_OPERATION_TIMEOUT,
        )

    def _default_delta_handler(self, delta: dict, responseStatus: str, token: str):
        logging.warning(
            f"unhandled delta of shadow: {delta}, {responseStatus}, {token}"
        )
        self.update_shadow(delta)

    def delta_handler_register(self, func: Callable):
        s = inspect.signature(func).parameters
        if len(s.items()) < 1:
            raise TypeError("delta_handler function must at least accept one argument")
        elif len(s.items()) > 3:
            raise TypeError(
                "delta_handler function must not accept more than three arguments"
            )
        self.__delta_handler = func

    def delta_handler_unregister(self):
        self.__delta_handler = self._default_delta_handler

    def __parse_delta(self, payload, responseStatus, token):
        payload = json.loads(payload)
        self._version = payload["version"]
        self._update_timestamp = payload["timestamp"]
        if not self.desired:
            self._full_state["desired"] = dict()
        self._full_state["desired"].update(payload["state"])
        self.__delta_handler(payload["state"], responseStatus, token)

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
        if update_state != {"state": dict()} or _is_parent_function(
            "__create_aws_handler"
        ):
            self.__shadow_handler.shadowUpdate(
                json.dumps(update_state),
                self.__callback_updating_shadow,
                MQTT_OPERATION_TIMEOUT,
            )
        else:
            self.__update_lock.release()

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
        self.__shadow_handler.shadowGet(
            self.__callback_get_shadow, MQTT_OPERATION_TIMEOUT
        )

    def delete_shadow(self) -> None:
        self.__shadow_handler.shadowDelete(
            self.__callback_deleting_shadow, MQTT_OPERATION_TIMEOUT
        )

    def __callback_updating_shadow(self, payload, responseStatus, token):
        if responseStatus == "accepted":
            payload = json.loads(payload)
            self._full_state["reported"] = _update_state_from_response(
                self._get_property_of_state("reported"),
                payload.get("state", dict()).get("reported", dict()),
            )
            logging.info("successfully updated shadow file")
        else:
            logging.critical(
                f"__callback_updating_shadow: not parsed response: {payload}"
            )

        try:
            if "delta" in responseStatus:
                self.__parse_delta(payload, responseStatus, token)
        finally:
            self.__update_lock.release()

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
