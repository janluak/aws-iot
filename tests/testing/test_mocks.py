def test_thing_mock():
    from aws_iot.testing.mock import MockThingHandler

    mock = MockThingHandler("TestThing", "eu-central-1", "asbf", "./")
    mock.thing.mqtt.connect()
    mock.thing.mqtt.connect.assert_called()

    mock.shadow.reported = {"test_state": True}
    assert mock.shadow.reported == {"test_state": True}
