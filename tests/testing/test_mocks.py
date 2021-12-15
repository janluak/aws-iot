def test_thing_mock():
    from aws_iot.testing.mock import MockThingHandler

    mock = MockThingHandler("TestThing", "eu-central-1", "asbf", "./")
    mock.thing.mqtt.connect()
    mock.thing.mqtt.connect.assert_called()

    mock.shadow.reported = {"test_state": True}
    assert mock.shadow.reported == {"test_state": True}

    mock.shadow.state.update({"state": {"desired": {"test_state": True}}})
    assert mock.shadow.desired == {"test_state": True}


def test_mock_reset():
    from aws_iot.testing.mock import MockThingHandler

    mock = MockThingHandler("TestThing", "eu-central-1", "asbf", "./")
    mock.thing.mqtt.connect()
    mock.thing.mqtt.connect.assert_called()

    mock.reset_mock()
    mock.thing.mqtt.connect.assert_not_called()

