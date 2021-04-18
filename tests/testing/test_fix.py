from pytest import mark
from moto import mock_iotdata
from boto3 import client
from json import dumps, loads
from aws_iot_handler.testing import *


test_state = {"state": {"desired": {"testData": "1"}}}
test_thing_names = ["TestThing1", "TestThing2", "AndAnotherTestThing"]


def _test_thing_shadow(iot_data_client, thing_name):
    shadow = loads(
        iot_data_client.get_thing_shadow(thingName=thing_name)["payload"].read()
    )

    assert set(shadow.keys()) == {"state", "metadata", "timestamp", "version"}
    assert not shadow["state"]
    assert not shadow["metadata"]
    assert isinstance(shadow["timestamp"], int)
    assert shadow["version"] == 1

    iot_data_client.update_thing_shadow(
        thingName=thing_name, payload=dumps(test_state),
    )

    shadow = loads(
        iot_data_client.get_thing_shadow(thingName=thing_name)["payload"].read()
    )
    assert set(shadow.keys()) == {"state", "metadata", "timestamp", "version"}
    assert shadow["state"] == {"delta": {"testData": "1"}, "desired": {"testData": "1"}}
    assert "testData" in shadow["metadata"]["desired"]
    assert shadow["version"] == 2
    assert isinstance(shadow["timestamp"], int)


@mark.parametrize(("thing_names", "region_name"), [(test_thing_names[0], "us-west-1")])
@mock_iotdata
def test_single_thing(clean_mocked_iot_shadows, thing_names, region_name):
    iot_data_client = client("iot-data", region_name=region_name)

    _test_thing_shadow(iot_data_client, thing_names)


@mark.parametrize(("thing_names", "region_name"), [(test_thing_names, "us-west-1")])
@mock_iotdata
def test_multiple_things(clean_mocked_iot_shadows, thing_names, region_name):
    iot_data_client = client("iot-data", region_name=region_name)

    for thing_name in thing_names:
        _test_thing_shadow(iot_data_client, thing_name)
