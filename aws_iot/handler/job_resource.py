from ._job import IoTJobHandler


__all__ = ["iot_job_resource"]


class IoTJobResourceController:
    def __init__(self, account_id: str = None):
        self.__iot_devices = dict()
        self.__account_id = account_id

    def __getitem__(self, iot_device_name: str) -> IoTJobHandler:
        if iot_device_name not in self.__iot_devices:
            self.__create_job_connection(iot_device_name)

        return self.__iot_devices[iot_device_name]

    def __create_job_connection(self, iot_device_name: str):
        self.__iot_devices[iot_device_name] = IoTJobHandler(
            iot_device_name, self.__account_id
        )


iot_job_resource = IoTJobResourceController()
