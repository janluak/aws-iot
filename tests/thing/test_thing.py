from pathlib import Path
from pytest import mark
from os import environ
from aws_iot_handler.thing import BaseIoTShadowClient


endpoint = "None"


class ShadowThing(BaseIoTShadowClient):
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


@mark.skipif(reason='endpoint=="None"')
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


@mark.skipif(reason='endpoint=="None"')
def test_smaller_update(test_env):
    sc = ShadowThing()

    sc.update_shadow({"new_state": 2})
    assert sc.reported == {"new_state": 2}

    sc.update_shadow({"next": "more"})
    assert sc.reported == {"new_state": 2, "next": "more"}


@mark.skip('ToDo')
def test_update_from_response(test_env):
    from aws_iot_handler.thing import _update_state_from_response
    ShadowThing._full_state = {"reported": {"key": "value"}}
    assert _update_state_from_response(ShadowThing, "") == {"key": "value"}
