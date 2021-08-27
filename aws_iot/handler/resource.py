from ._shadow import IoTShadowHandler
from os import environ


__all__ = ["iot_resource"]


class IoTResourceController:
    def __init__(self, account_id: str, endpoint_url: str = None):
        self.__iot_devices = dict()
        self.__account_id = account_id
        self.__endpoint_url = endpoint_url

    def __getitem__(self, iot_device_name: str) -> IoTShadowHandler:
        if iot_device_name not in self.__iot_devices:
            self.__create_shadow_connection(iot_device_name)

        return self.__iot_devices[iot_device_name]

    def __create_shadow_connection(self, iot_device_name: str):
        self.__iot_devices[iot_device_name] = IoTShadowHandler(
            iot_device_name, self.__endpoint_url
        )


iot_resource = IoTResourceController(
    environ["AWS_ACCOUNT_ID"] if "AWS_ACCOUNT_ID" in environ else None
)
