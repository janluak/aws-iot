from .shadow_handler import IoTShadowStaticHandler


__all__ = ["iot_shadow_resource"]


class IoTResourceController:
    def __init__(self):
        self.__iot_devices = dict()

    def __getitem__(self, iot_device_name: str) -> IoTShadowStaticHandler:
        if iot_device_name not in self.__iot_devices:
            self.__create_shadow_connection(iot_device_name)

        return self.__iot_devices[iot_device_name]

    def __create_shadow_connection(self, iot_device_name: str):
        self.__iot_devices[iot_device_name] = IoTShadowStaticHandler(iot_device_name)


iot_shadow_resource = IoTResourceController()
