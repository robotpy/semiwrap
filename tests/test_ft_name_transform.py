from swtest import ft


def test_snake_case_name_transform():
    assert ft.snake_get_http_server() == 1
    assert ft.snake_get_foo_value() == 2
    assert ft.snake_prefixed_value() == 3

    c = ft.NameTransformSnakeCases()
    assert c.snake_get_http_server() == 4
    assert c.snake_get_foo_value() == 5
    assert c.snake_prefixed_value() == 6
    assert c.snake_public_value == 7
    assert c.snake_http_server_value == 8
    assert c.snake_attr_value == 9

    assert ft.SnakeTransformEnum.value_one.value == 31
    assert ft.SnakeTransformEnum.http_server.value == 32
    assert ft.SnakeTransformEnum.prefixed_value.value == 33


def test_camel_case_name_transform():
    assert ft.camelGetHttpServer() == 11
    assert ft.camelGetFooValue() == 12
    assert ft.camelPrefixedValue() == 13

    c = ft.NameTransformCamelCases()
    assert c.camelGetHttpServer() == 14
    assert c.camelGetFooValue() == 15
    assert c.camelPrefixedValue() == 16
    assert c.camelPublicValue == 17
    assert c.camelHttpServerValue == 18
    assert c.camelAttrValue == 19

    assert ft.CamelTransformEnum.valueOne.value == 41
    assert ft.CamelTransformEnum.httpServer.value == 42
    assert ft.CamelTransformEnum.prefixedValue.value == 43


def test_pascal_case_name_transform():
    assert ft.PascalGetHttpServer() == 21
    assert ft.PascalGetFooValue() == 22
    assert ft.PascalPrefixedValue() == 23

    c = ft.NameTransformPascalCases()
    assert c.PascalGetHttpServer() == 24
    assert c.PascalGetFooValue() == 25
    assert c.PascalPrefixedValue() == 26
    assert c.PascalPublicValue == 27
    assert c.PascalHttpServerValue == 28
    assert c.PascalAttrValue == 29

    assert ft.PascalTransformEnum.ValueOne.value == 51
    assert ft.PascalTransformEnum.HttpServer.value == 52
    assert ft.PascalTransformEnum.PrefixedValue.value == 53


def test_rename_bypasses_name_transform_for_all_kinds():
    assert ft.ExactFunctionName() == 34
    assert ft.SnakeRenameEnum.ExactEnumValueName.value == 35

    c = ft.NameTransformSnakeRenameCases()
    assert c.ExactMethodName() == 36
    assert c.ExactAttributeName == 37

    assert not hasattr(ft, "exact_function_name")
    assert not hasattr(ft.SnakeRenameEnum, "exact_enum_value_name")
    assert not hasattr(c, "exact_method_name")
    assert not hasattr(c, "exact_attribute_name")
