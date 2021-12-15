from ..base_shadow import BaseShadow
from os import environ
import json

__all__ = ["IoTShadowHandler"]


IOT_ENDPOINT_URL = "https://{endpoint_id}.iot.{region_name}.amazonaws.com"


def _format_endpoint_url(endpoint: str, region_name: str):
    return IOT_ENDPOINT_URL.format(
        endpoint_id=endpoint.split("-")[0].split("/")[-1], region_name=region_name
    )


class IoTShadowHandler(BaseShadow):
    def __init__(
        self,
        thing_name: str,
        endpoint: str = None,
        region_name: str = None,
        client=None,
    ):
        self.__thing_name = thing_name
        self.__region_name = (
            environ["AWS_REGION"] if region_name is None else region_name
        )

        if client:
            self.__client = client
        elif endpoint:
            self.__client = client(
                "iot-data",
                region_name=self.__region_name,
                endpoint_url=_format_endpoint_url(endpoint, self.__region_name),
            )
        else:
            from ._iot_data_client import _iot_data_client

            self.__client = _iot_data_client

        super(IoTShadowHandler, self).__init__()

    @property
    def thing_name(self) -> str:
        return self.__thing_name

    @property
    def region_name(self) -> str:
        return self.__region_name

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
        response = self.__client.get_thing_shadow(thingName=self.thing_name)
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

        response = self.__client.update_thing_shadow(
            thingName=self.thing_name,
            payload=json.dumps({"state": {"desired": new_desired}}),
        )

        if response["ResponseMetadata"]["HTTPStatusCode"] != 200:
            raise ResourceWarning(response)
