import pytest

from semiwrap.name_transform import (
    NameTransformConfig,
    NameTransforms,
    merge_name_transform_configs,
    resolve_name_transform,
    resolve_name_transforms,
)


@pytest.mark.parametrize(
    "source, expected",
    [
        ("getFoo", "get_foo"),
        ("GetFoo", "get_foo"),
        ("get_foo", "get_foo"),
        ("GET_FOO", "get_foo"),
        ("HTTPServer", "http_server"),
        ("http_server", "http_server"),
        ("getFOO", "get_foo"),
        ("PascalCase_LikeThis", "pascal_case_like_this"),
    ],
)
def test_snake_case_transform(source, expected):
    transform = resolve_name_transform("snake_case")
    assert transform(source, "function") == expected


@pytest.mark.parametrize(
    "source, expected",
    [
        ("getFoo", "getFoo"),
        ("GetFoo", "getFoo"),
        ("get_foo", "getFoo"),
        ("GET_FOO", "getFoo"),
        ("HTTPServer", "httpServer"),
        ("http_server", "httpServer"),
        ("getFOO", "getFoo"),
        ("PascalCase_LikeThis", "pascalCaseLikeThis"),
    ],
)
def test_camel_case_transform(source, expected):
    transform = resolve_name_transform("camelCase")
    assert transform(source, "method") == expected


@pytest.mark.parametrize(
    "source, expected",
    [
        ("getFoo", "GetFoo"),
        ("GetFoo", "GetFoo"),
        ("get_foo", "GetFoo"),
        ("GET_FOO", "GetFoo"),
        ("HTTPServer", "HttpServer"),
        ("http_server", "HttpServer"),
        ("getFOO", "GetFoo"),
        ("PascalCase_LikeThis", "PascalCaseLikeThis"),
    ],
)
def test_pascal_case_transform(source, expected):
    transform = resolve_name_transform("PascalCase")
    assert transform(source, "attribute") == expected


@pytest.mark.parametrize(
    "source, expected",
    [
        ("getFoo", "GET_FOO"),
        ("GetFoo", "GET_FOO"),
        ("get_foo", "GET_FOO"),
        ("GET_FOO", "GET_FOO"),
        ("HTTPServer", "HTTP_SERVER"),
        ("http_server", "HTTP_SERVER"),
        ("getFOO", "GET_FOO"),
        ("PascalCase_LikeThis", "PASCAL_CASE_LIKE_THIS"),
    ],
)
def test_caps_case_transform(source, expected):
    transform = resolve_name_transform("CAPS_CASE")
    assert transform(source, "function") == expected


def test_none_transform_passes_cpp_name_through():
    transform = resolve_name_transform("none")
    assert transform("GetFoo", "function") == "GetFoo"
    assert transform("getFoo", "method") == "getFoo"
    assert transform("HTTPServer", "function") == "HTTPServer"
    assert transform("originalProp", "attribute") == "originalProp"


def test_default_transform_preserves_current_function_method_behavior():
    transform = resolve_name_transform("default")
    assert transform("GetFoo", "function") == "getFoo"
    assert transform("getFoo", "method") == "getFoo"
    assert transform("HTTPServer", "function") == "HTTPServer"


def test_default_transform_preserves_current_attribute_behavior():
    transform = resolve_name_transform("default")
    assert transform("GetFoo", "attribute") == "GetFoo"
    assert transform("originalProp", "attribute") == "originalProp"


try:
    from tests import name_transform_helpers
except ModuleNotFoundError:
    import name_transform_helpers

HELPER_MODULE = name_transform_helpers.__name__


def test_custom_transform_resolves_and_receives_kind():
    name_transform_helpers.reset()
    transform = resolve_name_transform(f"custom: {HELPER_MODULE}:custom_transform")
    assert transform("Thing", "attribute") == "attribute_Thing"
    assert name_transform_helpers.CALLS == 1


def test_custom_transform_resolution_is_cached():
    first = resolve_name_transform(f"custom: {HELPER_MODULE}:custom_transform")
    second = resolve_name_transform(f"custom: {HELPER_MODULE}:custom_transform")
    assert first is second


@pytest.mark.parametrize(
    "spec, message",
    [
        ("unknown", "unknown name_transform"),
        ("custom: missing_colon", "invalid custom name_transform"),
        (
            f"custom: {HELPER_MODULE}:missing",
            "does not define",
        ),
        (
            f"custom: {HELPER_MODULE}:not_callable",
            "is not callable",
        ),
    ],
)
def test_invalid_transform_specs(spec, message):
    with pytest.raises(ValueError, match=message):
        resolve_name_transform(spec)


def test_custom_transform_must_return_string():
    transform = resolve_name_transform(f"custom: {HELPER_MODULE}:returns_non_string")
    with pytest.raises(TypeError, match="returned int, expected str"):
        transform("Thing", "function")


def test_string_name_transform_applies_to_all_kinds():
    transforms = resolve_name_transforms("snake_case")
    assert transforms.function("GetFoo", "function") == "get_foo"
    assert transforms.method("GetFoo", "method") == "get_foo"
    assert transforms.attribute("GetFoo", "attribute") == "get_foo"
    assert transforms.enum_value("EnumValue", "enum_value") == "enum_value"


def test_mapping_name_transform_uses_default_for_missing_kinds():
    transforms = resolve_name_transforms(
        NameTransformConfig(default="snake_case", method="camelCase")
    )
    assert transforms.function("GetFoo", "function") == "get_foo"
    assert transforms.method("get_foo", "method") == "getFoo"
    assert transforms.attribute("GetFoo", "attribute") == "get_foo"
    assert transforms.enum_value("EnumValue", "enum_value") == "enum_value"


def test_mapping_name_transform_defaults_to_default_builtin_when_unset():
    transforms = resolve_name_transforms(NameTransformConfig(method="snake_case"))
    assert transforms.function("GetFoo", "function") == "getFoo"
    assert transforms.method("GetFoo", "method") == "get_foo"
    assert transforms.attribute("GetFoo", "attribute") == "GetFoo"
    assert transforms.enum_value("EnumValue", "enum_value") == "EnumValue"


def test_name_transform_mapping_merge_preserves_lower_precedence_fields():
    merged = merge_name_transform_configs(
        NameTransformConfig(default="snake_case", enum_value="PascalCase"),
        NameTransformConfig(method="camelCase"),
    )
    assert merged == NameTransformConfig(
        default="snake_case",
        function=None,
        method="camelCase",
        attribute=None,
        enum_value="PascalCase",
    )


def test_name_transform_mapping_merge_preserves_parameter_field():
    merged = merge_name_transform_configs(
        NameTransformConfig(default="snake_case", parameter="PascalCase"),
        NameTransformConfig(method="camelCase"),
    )
    assert merged == NameTransformConfig(
        default="snake_case",
        function=None,
        method="camelCase",
        attribute=None,
        enum_value=None,
        parameter="PascalCase",
    )


def test_name_transform_mapping_merge_inherits_known_words():
    merged = merge_name_transform_configs(
        NameTransformConfig(default="snake_case", known_words=["KiB"]),
        NameTransformConfig(method="camelCase"),
    )

    assert merged.known_words == ["KiB"]
    transforms = resolve_name_transforms(merged)
    assert transforms.function("GetKiBValue", "function") == "get_kib_value"


def test_name_transform_mapping_merge_empty_known_words_override_inherited_known_words():
    merged = merge_name_transform_configs(
        NameTransformConfig(default="snake_case", known_words=["KiB"]),
        NameTransformConfig(known_words=[]),
    )

    assert merged.known_words == []
    transforms = resolve_name_transforms(merged)
    assert transforms.function("GetKiBValue", "function") == "get_ki_b_value"


def test_name_transform_string_replaces_all_inherited_fields():
    merged = merge_name_transform_configs(
        NameTransformConfig(default="snake_case", enum_value="PascalCase"),
        "camelCase",
    )
    assert merged == NameTransformConfig(
        default="camelCase",
        function="camelCase",
        method="camelCase",
        attribute="camelCase",
        enum_value="camelCase",
        parameter="camelCase",
    )


def test_custom_transform_receives_enum_value_kind():
    name_transform_helpers.reset()
    transforms = resolve_name_transforms(
        NameTransformConfig(enum_value=f"custom: {HELPER_MODULE}:custom_transform")
    )
    assert transforms.enum_value("Thing", "enum_value") == "enum_value_Thing"


def test_string_name_transform_applies_to_parameters():
    transforms = resolve_name_transforms("snake_case")
    assert transforms.parameter("HTTPServerValue", "parameter") == "http_server_value"


def test_mapping_name_transform_can_override_parameter_kind():
    transforms = resolve_name_transforms(
        NameTransformConfig(default="snake_case", parameter="camelCase")
    )
    assert transforms.function("GetFoo", "function") == "get_foo"
    assert transforms.parameter("http_server_value", "parameter") == "httpServerValue"


def test_snake_case_transform_uses_configured_mixed_case_known_word():
    transform = resolve_name_transform("snake_case", known_words=("KiB",))
    assert transform("GetKiBValue", "function") == "get_kib_value"


def test_snake_case_transform_without_known_word_keeps_existing_split():
    transform = resolve_name_transform("snake_case")
    assert transform("GetKiBValue", "function") == "get_ki_b_value"


def test_known_word_matching_is_case_sensitive():
    exact = resolve_name_transform("snake_case", known_words=("mDNS",))
    mismatched = resolve_name_transform("snake_case", known_words=("MDNS",))

    assert exact("GetmDNSService", "function") == "get_mdns_service"
    assert mismatched("GetmDNSService", "function") == "getm_dns_service"


def test_longest_known_word_match_wins():
    transform = resolve_name_transform("snake_case", known_words=("Ki", "KiB"))
    assert transform("GetKiBValue", "function") == "get_kib_value"


def test_known_words_do_not_match_inside_all_caps_words():
    transform = resolve_name_transform("snake_case", known_words=("NT", "URL"))
    assert transform("ANTIQUE_WHITE", "attribute") == "antique_white"
    assert transform("BURLYWOOD", "attribute") == "burlywood"


def test_pluralized_known_words_keep_plural_suffix_at_word_boundary():
    snake = resolve_name_transform("snake_case", known_words=("OpMode",))
    caps = resolve_name_transform("CAPS_CASE", known_words=("OpMode",))

    assert snake("PublishOpModes", "function") == "publish_opmodes"
    assert snake("ClearOpModes", "function") == "clear_opmodes"
    assert snake("AddOpMode", "function") == "add_opmode"
    assert snake("GetOpModeOptions", "function") == "get_opmode_options"
    assert snake("GetOpModesOptions", "function") == "get_opmodes_options"
    assert caps("OpModes", "enum_value") == "OPMODES"
    assert caps("GetOpModes", "enum_value") == "GET_OPMODES"


def test_pluralized_known_word_suffix_requires_word_boundary():
    transform = resolve_name_transform("snake_case", known_words=("OpMode",))
    assert transform("OpModesetting", "function") == "opmode_setting"


def test_resolve_name_transforms_passes_known_words_to_all_builtin_kinds():
    transforms = resolve_name_transforms("snake_case", known_words=("KiB",))
    assert transforms.function("GetKiBValue", "function") == "get_kib_value"
    assert transforms.method("GetKiBValue", "method") == "get_kib_value"
    assert transforms.attribute("GetKiBValue", "attribute") == "get_kib_value"
    assert transforms.enum_value("KiBValue", "enum_value") == "kib_value"
    assert transforms.parameter("KiBValue", "parameter") == "kib_value"
