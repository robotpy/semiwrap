import pytest

from swtest.ft import _ft as ft


def test_defaults_make_default_arguments_keyword_only():
    assert ft.defaultArgsKwOnly(1) == 11
    assert ft.defaultArgsKwOnly(1, optional=2) == 3

    with pytest.raises(TypeError):
        ft.defaultArgsKwOnly(1, 2)


def test_function_false_allows_default_argument_positionally():
    assert ft.defaultArgsPositionalOptOut(1) == 21
    assert ft.defaultArgsPositionalOptOut(1, 2) == 3


def test_no_default_parameter_remains_positional():
    assert ft.noDefaultThenKwOnly(1, 2) == 33
    assert ft.noDefaultThenKwOnly(1, 2, keyword=3) == 6

    with pytest.raises(TypeError):
        ft.noDefaultThenKwOnly(1)
    with pytest.raises(TypeError):
        ft.noDefaultThenKwOnly(1, 2, 3)


def test_overload_false_overrides_enabled_default():
    assert ft.overloadKwOnlyOptOut(1, 2) == 3
    assert ft.overloadKwOnlyOptOut("value", suffix="?") == "value?"

    with pytest.raises(TypeError):
        ft.overloadKwOnlyOptOut("value", "?")


def test_overload_true_overrides_disabled_function():
    assert ft.overloadKwOnlyOptIn(1, 2) == 3
    assert ft.overloadKwOnlyOptIn("value", suffix="?") == "value?"

    with pytest.raises(TypeError):
        ft.overloadKwOnlyOptIn("value", "?")


def test_defaults_apply_to_methods():
    instance = ft.DefaultArgsMethod()
    assert instance.calculate(1) == 41
    assert instance.calculate(1, optional=2) == 3

    with pytest.raises(TypeError):
        instance.calculate(1, 2)

    assert instance.calculatePositional(1) == 51
    assert instance.calculatePositional(1, 2) == 3
