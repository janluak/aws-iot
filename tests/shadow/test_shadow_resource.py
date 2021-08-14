from boto3 import client
from moto import mock_iot, mock_iotdata
from os.path import dirname, realpath
from pytest import fixture
import json
from os import environ


test_state = {"test_key": "test_value"}


@mock_iotdata
def test_get_type_from_resource(setup_thing):

    iot_client = client("iot-data", region_name=environ["AWS_REGION"])
    iot_client.update_thing_shadow(
        thingName=environ["TestThingName"],
        payload=json.dumps({"state": {"reported": test_state}}),
    )

    from aws_iot.shadow.shadow_resource import iot_shadow_resource
    from aws_iot.shadow.shadow_handler import IoTShadowHandler

    assert issubclass(
        iot_shadow_resource[environ["TestThingName"]].__class__, IoTShadowHandler
    )


@mock_iotdata
def test_get_shadow_from_resource(setup_thing):

    iot_client = client("iot-data", region_name=environ["AWS_REGION"])
    iot_client.update_thing_shadow(
        thingName=environ["TestThingName"],
        payload=json.dumps({"state": {"reported": test_state}}),
    )

    from aws_iot.shadow.shadow_resource import iot_shadow_resource

    assert iot_shadow_resource[environ["TestThingName"]].reported == test_state
