from pytest import fixture
from pathlib import Path
from os import environ


@fixture(scope="session")
def mqtt_connection(test_env_real):
    from aws_iot.thing import IoTThingConnector
    t = IoTThingConnector(
        environ["TestThingName"],
        environ["AWS_REGION"],
        endpoint=environ["IOT_ENDPOINT"],
        cert_path=Path(Path(__file__).parent, "../certs")
    )
    t.connect()
    yield t
    t.disconnect()
