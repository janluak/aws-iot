from pathlib import Path
from pytest import mark
from os import environ
from aws_iot.thing import BaseIoTThing


endpoint = "None"


class ShadowThing(BaseIoTThing):
    def __init__(self):
        super(ShadowThing, self).__init__(
            environ["TestThingName"],
            environ["AWS_REGION"],
            endpoint=endpoint,
            cert_path=Path(Path(__file__).parent, "../certs"),
            delete_shadow_on_init=True
        )

    def handle_delta(self, *args):
        pass


class ShadowThingNoDeleting(BaseIoTThing):
    def __init__(self):
        super(ShadowThingNoDeleting, self).__init__(
            environ["TestThingName"],
            environ["AWS_REGION"],
            endpoint=endpoint,
            cert_path=Path(Path(__file__).parent, "../certs"),
        )

    def handle_delta(self, *args):
        pass


@mark.skipif(condition='endpoint=="None"')
def test_shadow_client_reported(test_env):
    sc = ShadowThing()

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
    sc = ShadowThing()

    sc.update_shadow({"new_state": 2})
    assert sc.reported == {"new_state": 2}

    sc.update_shadow({"next": "more"})
    assert sc.reported == {"new_state": 2, "next": "more"}
    sc.disconnect()


@mark.skipif(condition='endpoint=="None"')
def test_get_shadow_on_init(test_env):
    sc = ShadowThing()

    sc.update_shadow({"new_state": 2})
    assert sc.reported == {"new_state": 2}
    sc.disconnect()

    scnd = ShadowThingNoDeleting()
    assert scnd.reported != dict()
    scnd.disconnect()


@mark.skip('ToDo')
def test_update_from_response(test_env):
    from aws_iot.thing import _update_state_from_response
    ShadowThing._full_state = {"reported": {"key": "value"}}
    assert _update_state_from_response(ShadowThing, "") == {"key": "value"}
