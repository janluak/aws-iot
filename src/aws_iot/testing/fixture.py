from pytest import fixture
from json import dumps
from boto3 import client
from moto import mock_iot, mock_iotdata
from os import environ


region_name = environ["AWS_REGION"]
thing_names = environ["IOT_TEST_THING_NAMES"].split(",")


__all__ = [
    "setup_iot_things",
    "setup_mocked_iot_things",
    "clean_iot_shadows",
    "clean_mocked_iot_shadows",
]


def _setup_iot_thing(region_name, thing_names):
    if isinstance(thing_names, str):
        thing_names = [thing_names]

    iot_raw_client = client("iot", region_name=region_name)

    for thing_name in thing_names:
        iot_raw_client.create_thing(thingName=thing_name)


def _clear_iot_shadow(region_name, thing_names):
    if isinstance(thing_names, str):
        thing_names = [thing_names]

    iot_data_client = client("iot-data", region_name=region_name)
    for thing_name in thing_names:
        try:
            iot_data_client.delete_thing_shadow(thingName=thing_name)
        except iot_data_client.exceptions.ResourceNotFoundException:
            pass
        iot_data_client.update_thing_shadow(
            thingName=thing_name, payload=dumps({"state": dict()})
        )


@fixture
def setup_iot_things():
    _setup_iot_thing(region_name, thing_names)


@fixture
@mock_iot
def setup_mocked_iot_things():
    _setup_iot_thing(region_name, thing_names)


@fixture
def clean_iot_shadows(setup_iot_things):
    _clear_iot_shadow(region_name, thing_names)


@fixture
@mock_iotdata
def clean_mocked_iot_shadows(setup_mocked_iot_things):
    _clear_iot_shadow(region_name, thing_names)
