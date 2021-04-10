from aws_environ_helper import environ, update_nested_dict
from ._base_shadow import _BaseShadow
from boto3 import client
from json import loads, dumps
from abc import abstractmethod

__all__ = ["IoTShadowHandler"]


_iot_client = client("iot-data", region_name=environ["AWS_REGION"])


class IoTShadowHandler(_BaseShadow):
    @property
    def state(self):
        self.__refresh()
        return super().state

    @state.deleter
    def state(self):
        del self.desired

    @property
    def desired(self):
        return super().desired

    @desired.setter
    def desired(self, new_state: dict):
        self.__set_new_desired_state(new_state)

    @desired.deleter
    def desired(self):
        self.__set_new_desired_state(dict())

    def update(self, update_values: dict):
        self.__set_new_desired_state(update_values)

    def __refresh(self):
        response = _iot_client.get_thing_shadow(thingName=self.thing_name)
        payload = loads(response["payload"].read())
        self._full_state = payload["state"]
        self._meta = payload["metadata"]
        self._update_timestamp = payload["timestamp"]
        self._version = payload["version"]

    @property
    def meta(self):
        self.__refresh()
        return super().meta

    def _get_property_of_state(self, prop):
        self.__refresh()
        return super()._get_property_of_state(prop)

    def __set_new_desired_state(self, new_desired: dict):
        if not isinstance(new_desired, dict):
            raise TypeError("new desired state must be of type dict")

        response = _iot_client.update_thing_shadow(
            thingName=self.thing_name,
            payload=dumps({"state": {"desired": new_desired}}),
        )

        if response["ResponseMetadata"]["HTTPStatusCode"] != 200:
            raise ResourceWarning(response)
