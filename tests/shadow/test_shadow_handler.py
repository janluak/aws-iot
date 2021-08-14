from boto3 import client
from moto import mock_iotdata
from freezegun import freeze_time
from os import environ
import json
from pytest import mark
from copy import deepcopy

simple_test_state = {"test_key": "new_test_value"}
complex_test_state = {
    "level1": {"level2a": {"key1": 1, "key2": 2}, "level2b": {"key1": 1, "key2": 2}}
}


@mock_iotdata
def echo_desired_as_reported():
    from aws_iot.thing import _update_nested_dict
    iot_client = client("iot-data", region_name=environ["AWS_REGION"])
    payload = json.loads(
        iot_client.get_thing_shadow(thingName=environ["TestThingName"])["payload"].read()
    )
    desire = payload["state"]["desired"]
    iot_client.update_thing_shadow(
        thingName=environ["TestThingName"],
        payload=json.dumps({"state": {"reported": _update_nested_dict(
            payload["state"]["reported"] if "reported" in payload["state"] else dict(), desire), "desired": desire}}
        )
    )


@mock_iotdata
def test_get_shadow(setup_thing):
    iot_client = client("iot-data", region_name=environ["AWS_REGION"])
    iot_client.update_thing_shadow(
        thingName=environ["TestThingName"],
        payload=json.dumps({"state": {"reported": complex_test_state}}),
    )

    from aws_iot.shadow.shadow_handler import IoTShadowHandler

    iot_shadow = IoTShadowHandler(environ["TestThingName"])
    assert iot_shadow.reported == complex_test_state


@mock_iotdata
def test_set_shadow(setup_thing):
    from aws_iot.shadow.shadow_handler import IoTShadowHandler

    iot_shadow = IoTShadowHandler(environ["TestThingName"])
    iot_shadow.desired = complex_test_state

    assert iot_shadow.desired == complex_test_state

    iot_client = client("iot-data", region_name=environ["AWS_REGION"])
    payload = json.loads(
        iot_client.get_thing_shadow(thingName=environ["TestThingName"])["payload"].read()
    )

    assert payload["state"]["desired"] == complex_test_state
    assert payload["state"]["delta"] == complex_test_state

    assert iot_shadow.delta == complex_test_state


@mock_iotdata
@freeze_time("2020-01-01")
def test_get_shadow_meta(setup_thing):
    from aws_iot.shadow.shadow_handler import IoTShadowHandler

    iot_shadow = IoTShadowHandler(environ["TestThingName"])
    iot_shadow.desired = complex_test_state

    assert iot_shadow.meta == {
        "desired": {
            "level1": {
                "level2a": {
                    "key1": {"timestamp": 1577836800},
                    "key2": {"timestamp": 1577836800},
                },
                "level2b": {
                    "key1": {"timestamp": 1577836800},
                    "key2": {"timestamp": 1577836800},
                },
            }
        }
    }


@mock_iotdata
def test_foreign_updated_shadow(setup_thing):
    from aws_iot.shadow.shadow_handler import IoTShadowHandler

    iot_shadow = IoTShadowHandler(environ["TestThingName"])
    iot_shadow.desired = simple_test_state

    assert iot_shadow.desired == simple_test_state

    iot_client = client("iot-data", region_name=environ["AWS_REGION"])
    iot_client.update_thing_shadow(
        thingName=environ["TestThingName"],
        payload=json.dumps({"state": {"reported": {"test_key": "new_test_value"}}}),
    )

    assert iot_shadow.reported == {"test_key": "new_test_value"}


@mock_iotdata
@freeze_time("2020-01-01")
def test_unchangeable_properties(setup_thing):
    from aws_iot.shadow.shadow_handler import IoTShadowHandler

    iot_shadow = IoTShadowHandler(environ["TestThingName"])
    iot_shadow.desired = simple_test_state

    state = iot_shadow.reported
    state["test_key"] = "changed_test_value_state"
    assert state != iot_shadow.reported

    desired = iot_shadow.desired
    desired["test_key"] = "changed_test_value_desired"
    assert desired != iot_shadow.desired

    delta = iot_shadow.delta
    delta["test_key"] = "changed_test_value_delta"
    assert delta != iot_shadow.delta

    meta = iot_shadow.meta
    meta["desired"]["test_key"]["timestamp"] = 123
    assert meta != iot_shadow.meta


@mock_iotdata
def test_set_desired_and_retrieve_reported(setup_thing):
    from aws_iot.shadow.shadow_handler import IoTShadowHandler

    iot_shadow = IoTShadowHandler(environ["TestThingName"])
    iot_shadow.desired = complex_test_state

    assert iot_shadow.delta == complex_test_state

    echo_desired_as_reported()

    assert iot_shadow.reported == complex_test_state


@mock_iotdata
def test_set_desired_and_retrieve_reported_with_always_update_handler(setup_thing):
    from aws_iot.shadow.shadow_handler import IoTShadowHandler

    iot_shadow = IoTShadowHandler(environ["TestThingName"])
    iot_shadow.desired = complex_test_state

    assert iot_shadow.delta == complex_test_state

    echo_desired_as_reported()

    assert iot_shadow.reported == complex_test_state


@mock_iotdata
@freeze_time()
def test_update_part_of_state(setup_thing):
    from aws_iot.shadow.shadow_handler import IoTShadowHandler

    updated_complex_state = {
        "level1": {
            "level2a": {"key1": 1, "key2": "new_value"},
            "level2b": {"key1": 1, "key2": 2},
        }
    }

    iot_shadow = IoTShadowHandler(environ["TestThingName"])
    iot_shadow.desired = complex_test_state

    assert iot_shadow.desired == complex_test_state
    echo_desired_as_reported()
    assert iot_shadow.reported == complex_test_state

    update_data = {"level1": {"level2a": {"key2": "another_value"}}}
    iot_shadow.update_desired(update_data)

    expected_new_state = deepcopy(updated_complex_state)
    expected_new_state["level1"]["level2a"]["key2"] = "another_value"

    assert iot_shadow.desired == expected_new_state
    assert iot_shadow.reported != expected_new_state
    echo_desired_as_reported()
    assert iot_shadow.reported == expected_new_state


@mark.skip("bug in moto #3849: only updated keys are in meta available")
@mock_iotdata
def test_get_shadow_meta_with_partly_update(setup_thing):
    from aws_iot.shadow.shadow_handler import IoTShadowHandler

    iot_shadow = IoTShadowHandler(environ["TestThingName"])
    with freeze_time("2020-01-01"):
        iot_shadow.desired = complex_test_state

    assert iot_shadow.meta == {
        "desired": {
            "level1": {
                "level2a": {
                    "key1": {"timestamp": 1577836800},
                    "key2": {"timestamp": 1577836800},
                },
                "level2b": {
                    "key1": {"timestamp": 1577836800},
                    "key2": {"timestamp": 1577836800},
                },
            }
        }
    }

    with freeze_time("2020-01-02"):
        iot_shadow.update_desired({"level1": {"level2a": {"key2": "new_value"}}})

    assert iot_shadow.meta == {
        "desired": {
            "level1": {
                "level2a": {
                    "key1": {"timestamp": 1577836800},
                    "key2": {"timestamp": 1577923200},
                },
                "level2b": {
                    "key1": {"timestamp": 1577836800},
                    "key2": {"timestamp": 1577836800},
                },
            }
        }
    }


@mock_iotdata
def test_remove_desired_entry(setup_thing):
    from aws_iot.shadow.shadow_handler import IoTShadowHandler
    iot_shadow = IoTShadowHandler(environ["TestThingName"])

    iot_shadow.desired = complex_test_state
    assert iot_shadow.desired == complex_test_state

    iot_shadow.update_desired({"level1": {"level2b": None}})
    assert iot_shadow.desired == {"level1": {"level2a": {"key1": 1, "key2": 2}}}

    del iot_shadow.desired
    assert iot_shadow.desired == dict()
