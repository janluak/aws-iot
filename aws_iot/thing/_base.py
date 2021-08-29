from AWSIoTPythonSDK.MQTTLib import AWSIoTMQTTClient
from .. import _BaseIoT, _format_mqtt_endpoint
from abc import ABC
from pathlib import Path
import logging
from glob import glob
import json


__all__ = ["MQTT_OPERATION_TIMEOUT", "STANDARD_CERT_PATH", "_BaseIoTThing"]


MQTT_OPERATION_TIMEOUT = 5
STANDARD_CERT_PATH = "./certs"


class _BaseIoTThing(_BaseIoT, ABC):
    def __init__(
        self,
        thing_name: str,
        aws_region: str,
        endpoint: str,
        cert_path: (str, Path) = None,
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
        cert_path : str, Path
            directory of the certificates

        """
        if self.__already_initiated:
            return

        super(_BaseIoTThing, self).__init__(thing_name)
        self.__aws_region = aws_region
        self.__mqtt_endpoint = endpoint
        self.__cert_path = cert_path if cert_path else STANDARD_CERT_PATH
        self.__mqtt_client = None
        self._attached_clients = dict()
        self._connected = False

        self.__create_mqtt_client()

    @property
    def __already_initiated(self):
        if hasattr(self, "_connected"):
            return True
        else:
            return False

    def __create_mqtt_client(self):
        self.__mqtt_client = AWSIoTMQTTClient(self.thing_name)
        self.__mqtt_client.configureEndpoint(
            hostName=_format_mqtt_endpoint(self.__mqtt_endpoint, self.__aws_region),
            portNumber=8883,
        )

        self.__mqtt_client.configureCredentials(
            CAFilePath="{}/root-ca.pem".format(self.__cert_path),
            KeyPath=glob("{}/*-private.pem.key".format(self.__cert_path))[0],
            CertificatePath=glob("{}/*-certificate.pem.crt".format(self.__cert_path))[
                0
            ],
        )

        # AWSIoTMQTTShadowClient configuration
        self.__mqtt_client.configureAutoReconnectBackoffTime(1, 32, 20)
        self.__mqtt_client.configureConnectDisconnectTimeout(10)  # 10 sec
        self.__mqtt_client.configureMQTTOperationTimeout(
            MQTT_OPERATION_TIMEOUT
        )  # 5 sec

        self.__mqtt_client.connect()
        logging.info("connected to AWS")

    @property
    def mqtt(self) -> AWSIoTMQTTClient:
        return self.__mqtt_client

    def publish(
        self, topic: str, payload: [dict, list, str, float, int], service_level=1
    ):
        self.mqtt.publish(topic, json.dumps(payload), service_level)

    def disconnect(self):
        for i in self._attached_clients:
            i.disconnect()
        self.__mqtt_client.disconnect()
