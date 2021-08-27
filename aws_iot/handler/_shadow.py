from .. import _BaseIoT
from .._base_shadow import _BaseShadow
from os import environ
from boto3 import client
import json

__all__ = ["IoTShadowHandler"]


_client_data = {"region_name": environ["AWS_REGION"]}
if "IOT_ENDPOINT" in environ:
    _client_data.update({"endpoint_url": environ["IOT_ENDPOINT"]})
_iot_data_client = client("iot-data", **_client_data)


class IoTShadowHandler(_BaseIoT, _BaseShadow):
    def __init__(self, thing_name: str, endpoint_url: str = None):
        super(IoTShadowHandler, self).__init__(thing_name)
        if endpoint_url:
            global _iot_data_client
            _iot_data_client = client(
                "iot-data", region_name=environ["AWS_REGION"], endpoint_url=endpoint_url
            )

        super().__init__(thing_name)

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
        self.__set_new_desired_state(None)

    def update_desired(self, update_values: dict):
        self.__set_new_desired_state(update_values)

    def __refresh(self):
        response = _iot_data_client.get_thing_shadow(thingName=self.thing_name)
        payload = json.loads(response["payload"].read())
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

    def __set_new_desired_state(self, new_desired: (dict, None)):
        if not isinstance(new_desired, (dict, type(None))):
            raise TypeError("new desired state must be of type dict")

        response = _iot_data_client.update_thing_shadow(
            thingName=self.thing_name,
            payload=json.dumps({"state": {"desired": new_desired}}),
        )

        if response["ResponseMetadata"]["HTTPStatusCode"] != 200:
            raise ResourceWarning(response)
