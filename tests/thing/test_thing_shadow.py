from pathlib import Path
from pytest import raises
from os import environ
from unittest.mock import patch, MagicMock
from json import dumps


TIMEOUT = 10


def test_shadow_client_reported(iot_connector):
    from aws_iot.thing.shadow import ThingShadowHandler

    sc = ThingShadowHandler(
        delete_shadow_on_init=True, aws_thing_connector=iot_connector
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


def test_simple_update(iot_connector):
    from aws_iot.thing.shadow import ThingShadowHandler

    sc = ThingShadowHandler(
        aws_thing_connector=iot_connector,
        delete_shadow_on_init=True,
    )

    sc.update_shadow({"new_state": 2})
    assert sc.reported == {"new_state": 2}

    sc.update_shadow({"next": "more"})
    assert sc.reported == {"new_state": 2, "next": "more"}
    sc.thing.disconnect()


def test_get_shadow_on_init(test_env_real):
    from aws_iot.thing.shadow import ThingShadowHandler

    sc = ThingShadowHandler(
        environ["TestThingName"],
        environ["AWS_REGION"],
        environ["IOT_ENDPOINT"],
        Path(Path(__file__).parent.parent, "certs"),
        delete_shadow_on_init=True,
    )

    sc.update_shadow({"new_state": 2})
    assert sc.reported == {"new_state": 2}
    sc.thing.disconnect()

    scnd = ThingShadowHandler(
        environ["TestThingName"],
        environ["AWS_REGION"],
        environ["IOT_ENDPOINT"],
        Path(Path(__file__).parent.parent, "certs"),
    )
    assert scnd.reported != dict()
    scnd.thing.disconnect()


def test_context_of_connector_shadow_handler(test_env_real):
    from aws_iot.thing import IoTThingConnector
    from aws_iot.thing.shadow import ThingShadowHandler

    with IoTThingConnector(
        environ["TestThingName"],
        environ["AWS_REGION"],
        endpoint=environ["IOT_ENDPOINT"],
        cert_path=Path(Path(__file__).parent, "../certs"),
    ) as connector:
        sc = ThingShadowHandler(
            delete_shadow_on_init=True, aws_thing_connector=connector
        )

        sc.update_shadow({"new_state": 2})
        assert sc.reported == {"new_state": 2}

        sc.update_shadow({"next": "more"})
        assert sc.reported == {"new_state": 2, "next": "more"}


def test_add_delta_handler_signature_check(iot_connector):
    from aws_iot.thing.shadow import ThingShadowHandler

    sc = ThingShadowHandler(
        aws_thing_connector=iot_connector,
        delete_shadow_on_init=True,
    )

    def wrong_func():
        pass

    with raises(TypeError):
        sc.delta_handler_register(wrong_func)

    def correct_func(a, b, c):
        pass

    sc.delta_handler_register(correct_func)


@patch("src.aws_iot.thing.shadow.ThingShadowHandler._default_delta_handler")
def test_default_delta_handler(mock_default_handler, iot_connector):
    from src.aws_iot.thing.shadow import ThingShadowHandler

    sc = ThingShadowHandler(
        aws_thing_connector=iot_connector,
        delete_shadow_on_init=True,
    )

    payload = {
        "version": "1",
        "timestamp": 1234,
        "desired": dict(),
        "state": {"key": "value"},
    }
    parsed_payload = {"key": "value"}
    response_status = "okay"
    token = "token"

    sc._ThingShadowHandler__parse_delta(dumps(payload), response_status, token)
    mock_default_handler.assert_called_with(parsed_payload, response_status, token)
    mock_default_handler.reset_mock()

    handler_func = MagicMock()

    sc.delta_handler_register(handler_func)
    sc._ThingShadowHandler__parse_delta(dumps(payload), response_status, token)
    mock_default_handler.assert_not_called()
    handler_func.assert_called_with(parsed_payload, response_status, token)

    sc.delta_handler_unregister()
    sc._ThingShadowHandler__parse_delta(dumps(payload), response_status, token)
    mock_default_handler.assert_called_with(parsed_payload, response_status, token)
