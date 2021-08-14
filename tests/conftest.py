from os import environ, chdir, getcwd
from pathlib import Path
from pytest import fixture
import sys
from moto import mock_iot, mock_iotdata
from boto3 import client

modules_to_reload = ["tests", "src", "aws_iot"]


@fixture(scope="function")
def reload_modules():
    for key in list(sys.modules.keys()):
        if any(key.startswith(i) for i in modules_to_reload):
            del sys.modules[key]


class Config:
    TestThingName = "TestThing"
    AWS_REGION = "eu-central-1"
    IOT_ENDPOINT = "https://data.iot.eu-central-1.amazonaws.com"
    STAGE = "DEV"

    @classmethod
    def items(cls):
        return [(k, v) for k, v in cls.__dict__.items() if not k.startswith("__") and k not in ["items", "keys"]]

    @classmethod
    def keys(cls):
        return {k for k in cls.__dict__.keys() if not k.startswith("__") and k not in ["items", "keys"]}


@fixture
def test_env(reload_modules):
    for key, value in Config.items():
        environ[key] = value
    cwd = getcwd()
    chdir(Path(__file__).parent)
    yield Config
    chdir(cwd)
    for key in Config.keys():
        del environ[key]


@fixture
@mock_iot
def setup_thing(test_env, thing_name=Config.TestThingName):
    iot_raw_client = client("iot", region_name="eu-central-1")
    iot_raw_client.create_thing(thingName=thing_name)


@fixture
@mock_iotdata
def iot_resource(setup_thing, thing_name=Config.TestThingName):
    iot_data_client = client("iot-data", region_name="eu-central-1")
    iot_data_client.update_thing_shadow(thingName=thing_name,
                                        payload='{"state": {"desired": null, "reported": null}}')
    return iot_data_client
