from .shadow_handler import IoTShadowHandler


__all__ = ["iot_shadow_resource"]


class IoTResourceController:
    def __init__(self, endpoint_url: str = None):
        self.__iot_devices = dict()
        self.__endpoint_url = endpoint_url

    def __getitem__(self, iot_device_name: str) -> IoTShadowHandler:
        if iot_device_name not in self.__iot_devices:
            self.__create_shadow_connection(iot_device_name)

        return self.__iot_devices[iot_device_name]

    def __create_shadow_connection(self, iot_device_name: str):
        self.__iot_devices[iot_device_name] = IoTShadowHandler(iot_device_name, self.__endpoint_url)


iot_shadow_resource = IoTResourceController()
