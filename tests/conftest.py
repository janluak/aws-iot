from os import environ, chdir, getcwd
from pathlib import Path
from pytest import fixture
import sys, json
from moto import mock_iot, mock_iotdata
from boto3 import client

modules_to_reload = ["tests", "src", "aws_iot"]


@fixture(scope="function")
def reload_modules():
    for key in list(sys.modules.keys()):
        if any(key.startswith(i) for i in modules_to_reload):
            del sys.modules[key]


class _Config:
    @classmethod
    def items(cls):
        return [
            (k, v)
            for k, v in cls.__dict__.items()
            if not k.startswith("__") and k not in ["items", "keys"]
        ]

    @classmethod
    def keys(cls):
        return {
            k
            for k in cls.__dict__.keys()
            if not k.startswith("__") and k not in ["items", "keys"]
        }


class ConfigMoto(_Config):
    TestThingName = "TestThing"
    AWS_REGION = "eu-central-1"
    IOT_ENDPOINT = "https://data.iot.eu-central-1.amazonaws.com"
    AWS_ACCOUNT_ID = "1"
    STAGE = "DEV"


@fixture
def test_env_moto(reload_modules):
    stash = dict()
    for key, value in ConfigMoto.items():
        if env_key := environ.pop(key, None):
            stash[key] = env_key
        environ[key] = value
    cwd = getcwd()
    chdir(Path(__file__).parent)
    yield ConfigMoto
    chdir(cwd)
    for key in ConfigMoto.keys():
        del environ[key]
    for key in stash:
        environ[key] = stash[key]


@fixture(scope="session")
def test_env_real():
    cwd = getcwd()
    chdir(Path(__file__).parent)
    if Path(Path(__file__).parent, "certs/config.json").exists():
        with open("certs/config.json") as f:
            config = json.load(f)
        for key, value in config.items():
            if key not in environ:
                environ[key] = value
        yield
        chdir(cwd)
        for key in config.keys():
            del environ[key]
    else:
        yield


@fixture
@mock_iot
def setup_thing(test_env_moto, thing_name=ConfigMoto.TestThingName):
    iot_raw_client = client("iot", region_name="eu-central-1")
    resp = iot_raw_client.create_thing(thingName=thing_name)
    return resp["thingArn"]


@fixture
@mock_iotdata
def iot_resource(setup_thing, thing_name=ConfigMoto.TestThingName):
    iot_data_client = client("iot-data", region_name="eu-central-1")
    iot_data_client.update_thing_shadow(
        thingName=thing_name, payload='{"state": {"desired": null, "reported": null}}'
    )
    return iot_data_client


@fixture
def iot_connector(test_env_real):
    from src.aws_iot.thing.connector import IoTThingConnector

    c = IoTThingConnector(
        environ["TestThingName"],
        environ["AWS_REGION"],
        environ["IOT_ENDPOINT"],
        Path(Path(__file__).parent, "certs"),
    )
    with c:
        yield c
