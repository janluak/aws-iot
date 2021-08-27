from copy import deepcopy


def test_parent_function():
    from aws_iot.thing._shadow import _is_parent_function

    def calling_function():
        return _is_parent_function(test_parent_function.__name__)

    assert calling_function()

    assert not _is_parent_function(test_parent_function.__name__)


def test_delete_values_delta_none():
    from aws_iot.thing._shadow import _delete_values_if_present

    origin = {"key1": "value1"}
    compare = {"key2": "value2"}

    assert _delete_values_if_present(origin, compare) == {"key1": "value1"}


def test_delete_values_delete_all():
    from aws_iot.thing._shadow import _delete_values_if_present

    origin = {"key1": "value1"}
    compare = {"key1": "value1", "key2": "value2"}

    assert _delete_values_if_present(origin, compare) == dict()


def test_delete_values_delete_nested():
    from aws_iot.thing._shadow import _delete_values_if_present

    origin = {"key1": {"sub_key1": "value1"}}
    compare = {"key1": {"sub_key1": "value1"}, "key2": "value2"}

    assert _delete_values_if_present(origin, compare) == dict()


def test_delete_values_delete_different_nested_none():
    from aws_iot.thing._shadow import _delete_values_if_present

    origin = {"key1": {"sub_key1": "value1"}}
    compare = {"key1": {"sub_key1": "value1", "sub_key2": "value2"}, "key2": "value3"}

    assert _delete_values_if_present(origin, compare) == dict()


def test_delete_values_delete_different_nested_still_diff():
    from aws_iot.thing._shadow import _delete_values_if_present

    origin = {"key1": {"sub_key1": "value1", "sub_key3": "value4"}}
    compare = {"key1": {"sub_key1": "value1", "sub_key2": "value2"}, "key2": "value3"}

    assert _delete_values_if_present(origin, compare) == {
        "key1": {"sub_key3": "value4"}
    }


def test_delete_values_delete_list():
    from aws_iot.thing._shadow import _delete_values_if_present

    origin = {"key1": ["value1"]}
    compare = {"key1": ["value1", "value3"], "key2": "value2"}

    assert _delete_values_if_present(origin, compare) == {"key1": ["value1"]}


def test_delete_values_delete_nested_list():
    from aws_iot.thing._shadow import _delete_values_if_present

    origin = {"key1": {"sub_key1": ["value1", "value2"], "sub_key3": "value4"}}
    compare = {"key1": {"sub_key1": ["value1"]}, "key2": "value2"}

    assert _delete_values_if_present(origin, compare) == {
        "key1": {"sub_key1": ["value1", "value2"], "sub_key3": "value4"}
    }


def test_update_state_from_empty():
    from aws_iot.thing._shadow import _update_state_from_response

    old_reported_state = dict()
    update_reported_state = {"key": "value"}

    assert (
        _update_state_from_response(old_reported_state, update_reported_state)
        == update_reported_state
    )


def test_update_state_from_empty_nested():
    from aws_iot.thing._shadow import _update_state_from_response

    old_reported_state = dict()
    update_reported_state = {"key": {"sub_dict": "value"}}

    assert (
        _update_state_from_response(old_reported_state, update_reported_state)
        == update_reported_state
    )


def test_update_state_new_keys():
    from aws_iot.thing._shadow import _update_state_from_response

    old_reported_state = {"key": "value"}
    update_reported_state = {"new_key": "value"}

    assert _update_state_from_response(old_reported_state, update_reported_state) == {
        "key": "value",
        "new_key": "value",
    }


def test_update_state_update_keys():
    from aws_iot.thing._shadow import _update_state_from_response

    old_reported_state = {"key": "value"}
    update_reported_state = {"key": "new_value"}

    assert _update_state_from_response(old_reported_state, update_reported_state) == {
        "key": "new_value"
    }


def test_update_state_update_some_keys():
    from aws_iot.thing._shadow import _update_state_from_response

    old_reported_state = {"key": "value", "next_key": "next_value"}
    update_reported_state = {"key": "new_value"}

    assert _update_state_from_response(old_reported_state, update_reported_state) == {
        "key": "new_value",
        "next_key": "next_value",
    }


def test_update_state_update_nested_keys():
    from aws_iot.thing._shadow import _update_state_from_response

    old_reported_state = {
        "key": {"sub_dict": {"sub_sub1": "value", "sub_sub2": "value"}},
        "next_key": "next_value",
    }
    update_reported_state = {"key": {"sub_dict": {"sub_sub1": "new_value"}}}

    assert _update_state_from_response(old_reported_state, update_reported_state) == {
        "key": {"sub_dict": {"sub_sub1": "new_value", "sub_sub2": "value"}},
        "next_key": "next_value",
    }


def test_delete_state():
    from aws_iot.thing._shadow import _update_state_from_response

    old_reported_state = {"key": "value", "next_key": "next_value"}
    update_reported_state = {"key": None}

    assert _update_state_from_response(old_reported_state, update_reported_state) == {
        "next_key": "next_value"
    }


def test_delete_state_update_nested_keys():
    from aws_iot.thing._shadow import _update_state_from_response

    old_reported_state = {
        "key": {"sub_dict": {"sub_sub1": "value", "sub_sub2": "value"}},
        "next_key": "next_value",
    }
    update_reported_state = {"key": {"sub_dict": {"sub_sub1": None}}}

    assert _update_state_from_response(old_reported_state, update_reported_state) == {
        "key": {"sub_dict": {"sub_sub2": "value"}},
        "next_key": "next_value",
    }


def test_delete_all_reported():
    from aws_iot.thing._shadow import _update_state_from_response

    old_reported_state = {"key": "value"}
    update_reported_state = None

    assert (
        _update_state_from_response(old_reported_state, update_reported_state) == dict()
    )


from pytest import mark


@mark.skip("list implementation to check from AWS")
def test_update_state_update_nested_list():
    pass


# def test_set_value_if_not_present():
#     from aws_iot.thing import _set_values_to_None_if_not_in_present
#
#     origin = {"key1": "to_delete", "key2": {"key2.1": "to_delete", "key2.2": "to_keep"}}
#     compare = {"key2": {"key2.2": "other_value"}}


reference_dict = {
    "some_string": "abcdef",
    "some_int": 42,
    "some_float": 13.42,
    "some_dict": {"key1": "value1", "key2": 2},
    "some_nested_dict": {"KEY1": {"subKEY1": "subVALUE1", "subKEY2": 42.24}},
    "some_array": [
        "array_string",
        13,
        {"KEY1": {"arraySubKEY1": "subVALUE1", "arraySubKEY2": 42.24}},
    ],
}


def test_update_nested_key_reassignment():
    from aws_iot.thing._shadow import _update_nested_dict

    origin_dict = deepcopy(reference_dict)
    verify_dict = deepcopy(reference_dict)

    verify_dict["some_nested_dict"]["KEY1"]["subKEY1"] = "new Value"

    origin_dict = _update_nested_dict(
        origin_dict, {"some_nested_dict": {"KEY1": {"subKEY1": "new Value"}}}
    )
    assert origin_dict == verify_dict
    assert origin_dict["some_dict"] == verify_dict["some_dict"]


def test_update_nested_key_mutable():
    from aws_iot.thing._shadow import _update_nested_dict

    origin_dict = deepcopy(reference_dict)
    verify_dict = deepcopy(reference_dict)

    verify_dict["some_nested_dict"]["KEY1"]["subKEY1"] = "new Value"

    _update_nested_dict(
        origin_dict, {"some_nested_dict": {"KEY1": {"subKEY1": "new Value"}}}
    )
    assert origin_dict == verify_dict
    assert origin_dict["some_dict"] == verify_dict["some_dict"]


def test_update_part_of_nested_key_mutable():
    from aws_iot.thing._shadow import _update_nested_dict

    origin_dict = deepcopy(reference_dict)
    verify_dict = deepcopy(reference_dict)

    verify_dict["some_nested_dict"]["KEY1"]["subKEY1"] = "new Value"

    _update_nested_dict(
        origin_dict["some_nested_dict"], {"KEY1": {"subKEY1": "new Value"}}
    )
    assert origin_dict == verify_dict
    assert origin_dict["some_dict"] == verify_dict["some_dict"]
