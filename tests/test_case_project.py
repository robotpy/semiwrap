from swcase import case_test


def test_pyproject_name_transform_mapping_applies_to_wrapped_project():
    assert case_test.make_http_server_value() == 11

    item = case_test.CapsCaseThing(5)
    assert item.get_http_server_value() == 5
    assert item.add_foo_value(7) == 12
    assert item.public_http_value == 15

    assert case_test.CapsCaseEnum.VALUE_ONE.value == 21
    assert case_test.CapsCaseEnum.HTTP_SERVER.value == 22
    assert case_test.CapsCaseEnum.PREFIXED_VALUE.value == 23
