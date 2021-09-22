from pathlib import Path
from os import environ
from pytest import fail


def test_connection(test_env_real, caplog):
    from aws_iot.thing import IoTThingConnector

    t = IoTThingConnector(
        environ["TestThingName"],
        environ["AWS_REGION"],
        endpoint=environ["IOT_ENDPOINT"],
        cert_path=Path(Path(__file__).parent, "../certs")
    )
    t.connect()
    resp = t.publish("test_topic", {"some_payload": "some_value"})
    assert resp is True
    del t
    if len(caplog.messages) != 0:
        fail(str(caplog.messages))


def test_connection_context_manager(test_env_real, caplog):
    from aws_iot.thing import IoTThingConnector

    with IoTThingConnector(
        environ["TestThingName"],
        environ["AWS_REGION"],
        endpoint=environ["IOT_ENDPOINT"],
        cert_path=Path(Path(__file__).parent, "../certs")
    ) as t:
        resp = t.publish("test_topic", {"some_payload": "some_value"})
        assert resp is True

    assert t.connected is False
    if len(caplog.messages) != 0:
        fail(str(caplog.messages))
