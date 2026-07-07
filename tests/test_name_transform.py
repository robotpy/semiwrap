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
        ("CAN_S0", "can_s0"),
        ("WPI_TIMESRC_V4L_EOF", "wpi_timesrc_v4l_eof"),
        ("channel8Value", "channel8_value"),
        ("pose1", "pose1"),
        ("point2D", "point2_d"),
        ("vector3D", "vector3_d"),
        ("matrix4x4", "matrix4x4"),
        ("range0To5", "range0_to5"),
        ("getRotation2d", "get_rotation2d"),
        ("getLED8Bit", "get_led8_bit"),
        ("adc12BitValue", "adc12_bit_value"),
        ("protocol2Message", "protocol2_message"),
        ("version3Config", "version3_config"),
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
        ("getFoo", "kGetFoo"),
        ("GetFoo", "kGetFoo"),
        ("get_foo", "kGetFoo"),
        ("GET_FOO", "kGetFoo"),
        ("HTTPServer", "kHttpServer"),
        ("http_server", "kHttpServer"),
        ("getFOO", "kGetFoo"),
        ("PascalCase_LikeThis", "kPascalCaseLikeThis"),
        ("kFooBar", "kFooBar"),
    ],
)
def test_k_camel_case_transform(source, expected):
    transform = resolve_name_transform("kCamelCase")
    assert transform(source, "attribute") == expected


@pytest.mark.parametrize(
    "spec, expected",
    [
        ("snake_case", "foo_bar"),
        ("camelCase", "fooBar"),
        ("PascalCase", "FooBar"),
        ("CAPS_CASE", "FOO_BAR"),
    ],
)
def test_builtin_transforms_strip_k_camel_case_prefix(spec, expected):
    transform = resolve_name_transform(spec)
    assert transform("kFooBar", "enum_value") == expected


def test_builtin_transforms_do_not_strip_non_k_camel_case_prefix():
    snake = resolve_name_transform("snake_case")
    k_camel = resolve_name_transform("kCamelCase")

    assert snake("knownValue", "attribute") == "known_value"
    assert k_camel("known_value", "attribute") == "kKnownValue"


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
        ("CAN_S0", "CAN_S0"),
        ("WPI_TIMESRC_V4L_EOF", "WPI_TIMESRC_V4L_EOF"),
    ],
)
def test_caps_case_transform(source, expected):
    transform = resolve_name_transform("CAPS_CASE")
    assert transform(source, "function") == expected


@pytest.mark.parametrize(
    "spec, source, kind, expected",
    [
        ("snake_case", "_now", "method", "_now"),
        ("snake_case", "__private", "method", "__private"),
        ("snake_case", "_GetFPGATime", "method", "_get_fpga_time"),
        ("snake_case", "__GetFPGATime__", "method", "__get_fpga_time__"),
        ("camelCase", "_get_foo", "method", "_getFoo"),
        ("camelCase", "__private_name", "method", "__privateName"),
        ("PascalCase", "_get_foo", "attribute", "_GetFoo"),
        ("kCamelCase", "_get_foo", "attribute", "_kGetFoo"),
        ("kCamelCase", "__private_name", "attribute", "__kPrivateName"),
        ("CAPS_CASE", "_kValue", "enum_value", "_VALUE"),
        ("snake_case", "_kFooBar", "enum_value", "_foo_bar"),
        ("default", "_GetFoo", "method", "_getFoo"),
        ("default", "_HTTPServer", "function", "_HTTPServer"),
        ("none", "_GetFoo", "method", "_GetFoo"),
    ],
)
def test_builtin_transforms_preserve_leading_underscores(spec, source, kind, expected):
    transform = resolve_name_transform(spec)
    assert transform(source, kind) == expected


def test_builtin_known_word_matching_preserves_leading_underscores():
    transform = resolve_name_transform("snake_case", known_words=("KiB",))
    assert transform("_GetKiBValue", "function") == "_get_kib_value"
    assert transform("__KiBValue__", "attribute") == "__kib_value__"


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
