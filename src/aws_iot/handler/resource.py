from .handler import IoTHandler


__all__ = ["iot_resource"]


class IoTResourceController:
    def __init__(self, account_id: str = None, endpoint_url: str = None):
        self.__iot_devices = dict()
        self.__account_id = account_id
        self.__endpoint_url = endpoint_url

    def __getitem__(self, iot_device_name: str) -> IoTHandler:
        if iot_device_name not in self.__iot_devices:
            self.__create_mqtt_connection(iot_device_name)

        return self.__iot_devices[iot_device_name]

    def __create_mqtt_connection(self, iot_device_name: str):
        self.__iot_devices[iot_device_name] = IoTHandler(
            iot_device_name, account_id=self.__account_id, endpoint=self.__endpoint_url
        )


iot_resource = IoTResourceController()
