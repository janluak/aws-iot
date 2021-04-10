from boto3 import client
from moto import mock_iot, mock_iotdata
from os.path import dirname, realpath
from pytest import fixture
import json


test_thing_name = "TestThing"
test_state = {"test_key": "test_value"}


@fixture
@mock_iot
def iot_shadow_config():
    from aws_environ_helper import environ

    global environ
    environ._load_config_from_file(
        f"{dirname(realpath(__file__))}/shadow_wrapper_config.json"
    )

    iot_raw_client = client("iot", region_name=environ["AWS_REGION"])
    iot_raw_client.create_thing(thingName=test_thing_name)


@mock_iotdata
def test_get_type_from_resource(iot_shadow_config):

    iot_client = client("iot-data", region_name=environ["AWS_REGION"])
    iot_client.update_thing_shadow(
        thingName=test_thing_name,
        payload=json.dumps({"state": {"reported": test_state}}),
    )

    from aws_iot_handler.shadow.shadow_resource import iot_shadow_resource
    from aws_iot_handler.shadow.shadow_handler import IoTShadowHandler

    assert issubclass(
        iot_shadow_resource[test_thing_name].__class__, IoTShadowHandler
    )


@mock_iotdata
def test_get_shadow_from_resource(iot_shadow_config):

    iot_client = client("iot-data", region_name=environ["AWS_REGION"])
    iot_client.update_thing_shadow(
        thingName=test_thing_name,
        payload=json.dumps({"state": {"reported": test_state}}),
    )

    from aws_iot_handler.shadow.shadow_resource import iot_shadow_resource

    assert iot_shadow_resource[test_thing_name].reported == test_state
