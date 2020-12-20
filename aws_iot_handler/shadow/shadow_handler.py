from aws_environ_helper import environ, update_nested_dict
from boto3 import client
from json import loads, dumps
from copy import deepcopy


__all__ = ["IoTShadowStaticHandler"]


_iot_client = client("iot-data", region_name=environ["AWS_REGION"])


class IoTShadowStaticHandler:
    def __init__(self, iot_device_name):
        self.__device_name = iot_device_name
        self.__state = dict()
        self.__meta = dict()

        self.__fetch_timestamp = int()
        self.__version = int()

    def __get_property_of_state(self, prop):
        if not self.__fetch_timestamp:
            self.refresh()
        return deepcopy(self.__state[prop] if prop in self.__state else dict())

    @property
    def state(self):
        if not self.__fetch_timestamp:
            self.refresh()
        return deepcopy(self.__state)

    @state.deleter
    def state(self):
        del self.desired

    @property
    def reported(self):
        return self.__get_property_of_state("reported")

    @property
    def desired(self):
        return self.__get_property_of_state("desired")

    @desired.setter
    def desired(self, new_state: dict):
        self.__set_new_desired_state(new_state)

    @desired.deleter
    def desired(self):
        self.__set_new_desired_state(dict())

    @property
    def delta(self):
        return self.__get_property_of_state("delta")

    @property
    def meta(self):
        if not self.__fetch_timestamp:
            self.refresh()
        return deepcopy(self.__meta)

    def update(self, update_values):
        update_nested_dict(self.__state["desired"], update_values)
        self.__set_new_desired_state(self.__state["desired"])

    def __set_properties(self, payload):
        self.__state = payload["state"]
        self.__meta = payload["metadata"]
        self.__fetch_timestamp = payload["timestamp"]
        self.__version = payload["version"]

    def refresh(self):
        response = _iot_client.get_thing_shadow(thingName=self.__device_name)
        self.__set_properties(loads(response["payload"].read()))

    def __set_new_desired_state(self, new_desired):
        if not isinstance(new_desired, dict):
            raise TypeError("new desired state must be of type dict")

        response = _iot_client.update_thing_shadow(
            thingName=self.__device_name,
            payload=dumps({"state": {"desired": new_desired}}),
        )

        if response["ResponseMetadata"]["HTTPStatusCode"] == 200:
            self.__set_properties(loads(response["payload"].read()))

        else:
            raise ResourceWarning(response)
