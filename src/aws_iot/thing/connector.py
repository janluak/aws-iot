import AWSIoTPythonSDK.exception.AWSIoTExceptions
from AWSIoTPythonSDK.MQTTLib import AWSIoTMQTTClient
from pathlib import Path
import logging
from glob import glob
import json

__all__ = [
    "IoTThingConnector",
    "MQTT_OPERATION_TIMEOUT",
    "MQTT_DISCONNECT_TIMEOUT",
    "BASE_RECONNECT_QUIET_TIME_SECOND",
    "MAX_RECONNECT_QUIET_TIME_SECOND",
    "STABLE_CONNECTION_TIME_SECOND",
    "STANDARD_CERT_PATH",
    "QUALITY_OF_SERVICE_AT_LEAST_ONCE",
    "QUALITY_OF_SERVICE_AT_MOST_ONCE",
]

IOT_ENDPOINT_URL = "{endpoint_id}-ats.iot.{region_name}.amazonaws.com"

MQTT_OPERATION_TIMEOUT = 5
MQTT_DISCONNECT_TIMEOUT = 10
BASE_RECONNECT_QUIET_TIME_SECOND = 1
MAX_RECONNECT_QUIET_TIME_SECOND = 32
STABLE_CONNECTION_TIME_SECOND = 20

QUALITY_OF_SERVICE_AT_MOST_ONCE = 0
QUALITY_OF_SERVICE_AT_LEAST_ONCE = 1

STANDARD_CERT_PATH = "./certs"


class IoTThingConnector:
    def __init__(
        self,
        thing_name: str,
        aws_region: str,
        endpoint: str,
        cert_path: (str, Path) = STANDARD_CERT_PATH,
        operation_timeout: int = MQTT_OPERATION_TIMEOUT,
        base_reconnect_quiet_time_second: int = BASE_RECONNECT_QUIET_TIME_SECOND,
        max_reconnect_quiet_time_second: int = MAX_RECONNECT_QUIET_TIME_SECOND,
        stable_connection_time_second: int = STABLE_CONNECTION_TIME_SECOND,
        disconnect_timeout: int = MQTT_DISCONNECT_TIMEOUT,
    ):
        """

        Parameters
        ----------
        thing_name : str
            the name of the AWS thing.
            needs to be identical to the name of an AWS thing as configured in the management console
        aws_region : str
            region of AWS thing management
        endpoint : str
            MQTT enpoint of the desired AWS account
        cert_path : str, Path, optional
            directory of the certificates

        operation_timeout : int, optional
        base_reconnect_quiet_time_second : int, optional
        max_reconnect_quiet_time_second : int, optional
        stable_connection_time_second : int, optional
        disconnect_timeout : int, optional
        """
        self.__thing_name = thing_name
        self.__aws_region = aws_region
        self.__mqtt_endpoint = endpoint
        self.__cert_path = cert_path

        self.__mqtt_operation_timeout = operation_timeout
        self.__mqtt_base_reconnect_quiet_time_second = base_reconnect_quiet_time_second
        self.__mqtt_max_reconnect_quiet_time_second = max_reconnect_quiet_time_second
        self.__mqtt_stable_connection_time_second = stable_connection_time_second
        self.__mqtt_disconnect_timeout = disconnect_timeout

        self.__connected: bool = False

        self.__mqtt_client = AWSIoTMQTTClient(self.thing_name)
        self.__configure_mqtt_client()

    @property
    def thing_name(self) -> str:
        return self.__thing_name

    @property
    def mqtt(self) -> AWSIoTMQTTClient:
        return self.__mqtt_client

    @property
    def connected(self) -> bool:
        return self.__connected

    def __configure_mqtt_client(self):
        hostname = IOT_ENDPOINT_URL.format(
            endpoint_id=self.__mqtt_endpoint.split("-")[0].split("/")[-1],
            region_name=self.__aws_region,
        )

        self.mqtt.configureEndpoint(
            hostName=hostname,
            portNumber=8883,
        )

        self.mqtt.configureCredentials(
            CAFilePath="{}/root-ca.pem".format(self.__cert_path),
            KeyPath=glob("{}/*-private.pem.key".format(self.__cert_path))[0],
            CertificatePath=glob("{}/*-certificate.pem.crt".format(self.__cert_path))[
                0
            ],
        )

        # AWSIoTMQTTShadowClient configuration
        self.mqtt.configureAutoReconnectBackoffTime(
            self.__mqtt_base_reconnect_quiet_time_second,
            self.__mqtt_max_reconnect_quiet_time_second,
            self.__mqtt_stable_connection_time_second,
        )
        self.mqtt.configureConnectDisconnectTimeout(self.__mqtt_disconnect_timeout)
        self.mqtt.configureMQTTOperationTimeout(self.__mqtt_operation_timeout)

    def connect(self):
        self.mqtt.connect()
        self.__connected = True
        logging.info("connected to AWS")

    def disconnect(self):
        try:
            self.mqtt.disconnect()
        except AWSIoTPythonSDK.exception.AWSIoTExceptions.disconnectError:
            pass
        self.__connected = False
        logging.info("disconnected from AWS")

    def publish(
        self,
        topic: str,
        payload: [dict, list, str, float, int],
        service_level: int = QUALITY_OF_SERVICE_AT_LEAST_ONCE,
    ):
        return self.mqtt.publish(topic, json.dumps(payload), service_level)

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.disconnect()

    def __del__(self):
        self.disconnect()
