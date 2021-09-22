from pathlib import Path
from . import mqtt_connection
from pytest import mark, fixture
from os import environ


TIMEOUT = 10


@fixture
def shadow_thing_handler():
    from aws_iot.thing import ThingShadowHandler

    class ShadowThing(ThingShadowHandler):
        def handle_delta(self, *args):
            pass

    yield ShadowThing


def test_shadow_client_reported(mqtt_connection, shadow_thing_handler):
    sc = shadow_thing_handler(
        aws_thing_connector=mqtt_connection,
        delete_shadow_on_init=True,
    )

    sc.reported = {"new_state": 1}
    assert sc.reported == {"new_state": 1}
    assert sc._full_state == {"reported": {"new_state": 1}}

    del sc.reported
    assert sc.reported == dict()

    sc.update_shadow({"new_state": 2})
    assert sc.reported == {"new_state": 2}

    sc.update_shadow({"next": "more"})
    assert sc.reported == {"new_state": 2, "next": "more"}
    sc.thing.disconnect()


def test_simple_update(mqtt_connection, shadow_thing_handler):
    sc = shadow_thing_handler(
        aws_thing_connector=mqtt_connection,
        delete_shadow_on_init=True,
    )

    sc.update_shadow({"new_state": 2})
    assert sc.reported == {"new_state": 2}

    sc.update_shadow({"next": "more"})
    assert sc.reported == {"new_state": 2, "next": "more"}
    sc.thing.disconnect()


def test_get_shadow_on_init(mqtt_connection, shadow_thing_handler):
    sc = shadow_thing_handler(
        aws_thing_connector=mqtt_connection,
        delete_shadow_on_init=True,

    )

    sc.update_shadow({"new_state": 2})
    assert sc.reported == {"new_state": 2}
    sc.thing.disconnect()

    scnd = shadow_thing_handler(
        environ["TestThingName"],
        environ["AWS_REGION"],
        endpoint=environ["IOT_ENDPOINT"],
        cert_path=Path(Path(__file__).parent, "../certs"),
    )
    assert scnd.reported != dict()
    scnd.thing.disconnect()


def test_context_of_connector_shadow_handler(test_env_real, shadow_thing_handler):
    from aws_iot.thing import IoTThingConnector

    with IoTThingConnector(
            environ["TestThingName"],
            environ["AWS_REGION"],
            endpoint=environ["IOT_ENDPOINT"],
            cert_path=Path(Path(__file__).parent, "../certs")
    ) as connector:
        sc = shadow_thing_handler(
            delete_shadow_on_init=True,
            aws_thing_connector=connector
        )

        sc.update_shadow({"new_state": 2})
        assert sc.reported == {"new_state": 2}

        sc.update_shadow({"next": "more"})
        assert sc.reported == {"new_state": 2, "next": "more"}

