from AWSIoTPythonSDK.MQTTLib import AWSIoTMQTTShadowClient
from AWSIoTPythonSDK.exception.AWSIoTExceptions import *
from AWSIoTPythonSDK.core.shadow.deviceShadow import deviceShadow
from .shadow._base_shadow import _BaseShadow
from abc import ABC, abstractmethod
from threading import Thread, Lock
from glob import glob
from pathlib import Path
import logging
import inspect
import json
from collections.abc import Mapping

__all__ = ["BaseIoTThing"]

MQTT_OPERATION_TIMEOUT = 5


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


def _delete_values_if_present(origin: dict, compare: dict, set_value_to_None: bool = False) -> dict:
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

    change = {
        False: delete,
        True: set_to_none
    }[set_value_to_None]

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


def _set_values_to_None_if_not_in_present(origin: dict, compare: dict) -> dict:
    """
    Set all key-value-pairs in origin to None if key present in `compare`

    Parameters
    ----------
    origin : dict
        the original dictionary to set values to None if key not present in `compare`
    compare : dict
        the dictionary to compare the origin to

    Returns
    -------
    origin : dict
        the original dictionary without the values set to None

    """

    for key in origin.copy():
        if key not in compare:
            origin[key] = None
        if isinstance(origin[key], dict):
            origin[key] = _delete_values_if_present(origin[key], compare[key])
        elif compare[key] == origin[key]:
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
                reported_state[key] = _update_state_from_response(reported_state[key], response[key])
            except KeyError:
                reported_state[key] = value
        else:
            reported_state[key] = value

    return reported_state


class BaseIoTThing(_BaseShadow, ABC):
    """
    Custom AWS thing shadow taking care of the underlying functions used in all AWS shadows for the coffee machine
    """

    def __init__(
        self,
        thing_name: str,
        aws_region: str,
        endpoint: str,
        cert_path: (str, Path) = "./certs",
        delete_shadow_on_init=False
    ):
        """
        Parameters
        ----------
        thing_name : str
            the name of the AWS thing. needs to be identical to the name of an AWS thing as configured in the management console
            is also used for loading the correct certs
        aws_region : str
            region of AWS thing management
        endpoint : str
            MQTT enpoint of the desired AWS account
        cert_path : str, Path
            directory of the certificates
        delete_shadow_on_init : bool
            if True: shadow is deleted on every new instantiation

        """
        super().__init__(thing_name)
        self.__aws_region = aws_region
        self.__mqtt_endpoint = endpoint
        self.__cert_path = cert_path
        self.__delete_shadow_on_init = delete_shadow_on_init

        self.__cache_new_state = dict()

        self.__update_lock = Lock()

        self.__create_aws_mqtt_shadow_client()
        self.__create_aws_handler()
        # self.log.success("finished initialization of object " + self.__class__.__name__)

    def __create_aws_mqtt_shadow_client(self):
        """
        Initializes the AWSIoTMQTTShadowClient mqtt broker

        """
        self.__mqtt_client = AWSIoTMQTTShadowClient(self.thing_name)

        self.__mqtt_client.configureEndpoint(
            hostName=f"{self.__mqtt_endpoint}-ats.iot.{self.__aws_region}.amazonaws.com",
            portNumber=8883
        )

        self.__mqtt_client.configureCredentials(
            CAFilePath="{}/root-ca.pem".format(self.__cert_path),
            KeyPath=glob("{}/*-private.pem.key".format(self.__cert_path))[0],
            CertificatePath=glob("{}/*-certificate.pem.crt".format(self.__cert_path))[0]
        )

        # AWSIoTMQTTShadowClient configuration
        self.__mqtt_client.configureAutoReconnectBackoffTime(1, 32, 20)
        self.__mqtt_client.configureConnectDisconnectTimeout(10)  # 10 sec
        self.__mqtt_client.configureMQTTOperationTimeout(MQTT_OPERATION_TIMEOUT)  # 5 sec

        self.__mqtt_client.connect()
        logging.info("connected to AWS")

    def __create_aws_handler(self):
        """
        Create the handler for the AWS IoT shadow handler
        """

        self.__shadow_handler = self._shadow_client.createShadowHandlerWithName(
            shadowName=self.thing_name,
            isPersistentSubscribe=True
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
            raise TypeError(f"new reported state must be of type dict, provided {type(new_state)}")

        self.update_shadow(new_state)

    @reported.deleter
    def reported(self):
        self.update_shadow(None)

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

    def update_shadow(self, new_state: (dict, None) = None, clear_desired: bool = False):
        self.__update_lock.acquire()

        if self.__cache_new_state:
            if new_state is None:
                new_state = dict()
            new_state = _update_nested_dict(new_state, self.__cache_new_state)
            self.__cache_new_state = dict()

        update_state = {"state": {"reported": new_state}}
        # ToDo remove all keys in new_state if already present in reported -> not getting updated
        if clear_desired:
            update_state["state"]["desired"] = _delete_values_if_present(self.desired, new_state, True)

        self._shadow_handler.shadowUpdate(
            json.dumps(update_state),
            self.__callback_updating_shadow,
            MQTT_OPERATION_TIMEOUT
        )

    def delete_shadow(self) -> None:
        self._shadow_handler.shadowDelete(self.__callback_deleting_shadow, MQTT_OPERATION_TIMEOUT)

    @property
    def _shadow_client(self) -> AWSIoTMQTTShadowClient:
        return self.__mqtt_client

    @property
    def _shadow_handler(self) -> deviceShadow:
        return self.__shadow_handler

    def __callback_updating_shadow(self, payload, responseStatus, token):
        # print(f"callback update shadow: {payload=}, {responseStatus=}, {token=}")
        if responseStatus == "accepted":
            payload = json.loads(payload)
            self._full_state["reported"] = _update_state_from_response(
                self._get_property_of_state("reported"), payload["state"]["reported"]
            )
            # print("successfully updated shadow file")
            logging.info("successfully updated shadow file")
        else:
            logging.critical(f"__callback_updating_shadow: not parsed response: {payload}")

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
                logging.error("something went wrong with cleaning the shadow file. Response from AWS: " + str(args))

    def publish(self, topic: str, payload: [dict, list, str, float, int], service_level=1):
        self.__mqtt_client.getMQTTConnection().publish(topic, json.dumps(payload), service_level)
