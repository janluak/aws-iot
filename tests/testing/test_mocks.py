def test_thing_mock():
    from aws_iot.testing.mock import MockThingHandler

    mock = MockThingHandler("TestThing", "eu-central-1", "asbf", "./")
    mock.thing.mqtt.connect()
    mock.thing.mqtt.connect.assert_called()

    mock.shadow.reported = {"test_state": True}
    assert mock.shadow.reported == {"test_state": True}

    mock.shadow.state.update({"state": {"desired": {"test_state": True}}})
    assert mock.shadow.desired == {"test_state": True}
    mock.__del__()


def test_mock_reset():
    from aws_iot.testing.mock import MockThingHandler

    mock = MockThingHandler("TestThing", "eu-central-1", "asbf", "./")
    mock.thing.mqtt.connect()
    mock.thing.mqtt.connect.assert_called()

    mock.reset_mock()
    mock.thing.mqtt.connect.assert_not_called()


def test_mock_connector_publish_reset():
    from aws_iot.testing.mock import MockConnector
    mock = MockConnector("test_name")
    mock.publish(123)
    mock.publish.assert_called()
    mock.reset_mock()
    mock.publish.assert_not_called()
    mock.publish(123)

    mock = MockConnector("test_name")
    mock.publish.assert_not_called()


