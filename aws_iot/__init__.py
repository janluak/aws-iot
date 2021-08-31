__version__ = "0.2.3"


class _BaseIoT:
    def __init__(self, thing_name, *args):
        self.__thing_name = thing_name

    @property
    def thing_name(self) -> str:
        return self.__thing_name


def _format_mqtt_endpoint(endpoint, region):
    endpoint = endpoint.split("-")[0]
    endpoint = endpoint.split("/")[-1]
    return f"{endpoint}-ats.iot.{region}.amazonaws.com"
