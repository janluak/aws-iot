from pathlib import Path
from pytest import mark
from os import environ


endpoint = "None"


def create_shadow_thing_with_clear_shadow():
    from aws_iot.thing import IoTShadowThing

    class ShadowThingDeletingOnInit(IoTShadowThing):
        def __init__(self):
            super(ShadowThingDeletingOnInit, self).__init__(
                environ["TestThingName"],
                environ["AWS_REGION"],
                endpoint=endpoint,
                cert_path=Path(Path(__file__).parent, "../certs"),
                delete_shadow_on_init=True,
            )

        def handle_delta(self, *args):
            pass

    return ShadowThingDeletingOnInit


def create_shadow_thing_with_consistent_shadow():
    from aws_iot.thing import IoTShadowThing

    class ShadowThingNoDeleting(IoTShadowThing):
        def __init__(self):
            super(ShadowThingNoDeleting, self).__init__(
                environ["TestThingName"],
                environ["AWS_REGION"],
                endpoint=endpoint,
                cert_path=Path(Path(__file__).parent, "../certs"),
            )

        def handle_delta(self, *args):
            pass

    return ShadowThingNoDeleting


@mark.skipif(condition='endpoint=="None"')
def test_shadow_client_reported(test_env):
    sc = create_shadow_thing_with_clear_shadow()()

    sc.reported = {"new_state": 1}
    assert sc.reported == {"new_state": 1}
    assert sc._full_state == {"reported": {"new_state": 1}}

    del sc.reported
    assert sc.reported == dict()

    sc.update_shadow({"new_state": 2})
    assert sc.reported == {"new_state": 2}

    sc.update_shadow({"next": "more"})
    assert sc.reported == {"new_state": 2, "next": "more"}
    sc.disconnect()


@mark.skipif(condition='endpoint=="None"')
def test_smaller_update(test_env):
    sc = create_shadow_thing_with_clear_shadow()()

    sc.update_shadow({"new_state": 2})
    assert sc.reported == {"new_state": 2}

    sc.update_shadow({"next": "more"})
    assert sc.reported == {"new_state": 2, "next": "more"}
    sc.disconnect()


@mark.skipif(condition='endpoint=="None"')
def test_get_shadow_on_init(test_env):
    sc = create_shadow_thing_with_clear_shadow()()

    sc.update_shadow({"new_state": 2})
    assert sc.reported == {"new_state": 2}
    sc.disconnect()

    scnd = create_shadow_thing_with_consistent_shadow()()
    assert scnd.reported != dict()
    scnd.disconnect()


@mark.skip("ToDo")
def test_update_from_response(test_env):
    from aws_iot.thing._shadow import _update_state_from_response
    shadow_thing = create_shadow_thing_with_clear_shadow()

    shadow_thing._full_state = {"reported": {"key": "value"}}
    assert _update_state_from_response(shadow_thing, "") == {"key": "value"}
