from swtest import ft
import pytest


def test_native_enums():
    import enum
    from swtest.ft import _ft as ft

    assert ft.NativeColor.__bases__ == (enum.Enum,)
    assert ft.NativeNumber.__bases__ == (enum.IntEnum,)
    assert ft.NativeFlags.__bases__ == (enum.Flag,)
    assert ft.NativeIntFlags.__bases__ == (enum.IntFlag,)
    assert ft.NativeColor.Red != 1
    assert ft.NativeNumber.One == 1
    assert (ft.NativeFlags.A | ft.NativeFlags.B).value == 3
    assert ft.NativeIntFlags.A | ft.NativeIntFlags.B == 3
    assert ft.NativeColor.Red.a_method() == 11
    assert ft.NativeColor.Blue.a_method() == 12
    assert ft.NativeColor.Alias is ft.NativeColor.Red
    assert ft.Red is ft.NativeColor.Red
    cls = ft.NativeContainer
    assert cls.Color.Alias is cls.Color.Red
    assert cls.Red is cls.Color.Red
    assert cls.echo() is cls.Color.Red
    assert cls.echo(cls.Color.Blue) is cls.Color.Blue
    assert ft.native_inline_ran is True
    assert ft.NativeTemplateInt.echo() is ft.NativeTemplateInt.Color.Red
    for outer in (ft.NativeTemplateInt, ft.NativeContainer):
        assert outer.Inner.Color.__bases__ == (enum.Enum,)
        assert outer.Inner.Color.Red.value == 1
        assert outer.Inner.Deep.Color.__bases__ == (enum.Enum,)
        assert outer.Inner.Deep.Color.Blue.value == 2


def test_enums():
    # normal enums convert to integers
    assert ft.GEnum.GE1 == 1
    assert ft.NSGEnum.NSGE2 == 2
    assert ft.EnumContainer.InnerEnum.IE1 == 1
    assert ft.NSEnumContainer.InnerEnum.NSIE1 == 1
    assert ft.NSEnumContainer2.InnerEnumContainer.MoreInnerEnum.NSIEMIE1 == 1

    # Unnamed enums are hoisted as integers to their scope
    # - not supported yet for globals
    # assert ft._ft.UGEX == 7
    # assert ft._ft.NSUGEX == 5
    assert ft.EnumContainer.UEX == 4

    # enum class are specific types
    assert "GCE1" in ft.GCEnum.GCE1.__members__
    assert "NSGE2" in ft.NSGCEnum.NSGE2.__members__
    assert "IEC1" in ft.EnumContainer.InnerCEnum.__members__
    assert "NSIEC1" in ft.NSEnumContainer.InnerCEnum.__members__
    assert (
        "NSIEMIEC1" in ft.NSEnumContainer2.InnerEnumContainer.MoreInnerCEnum.__members__
    )


def test_enum_header_inline_code():
    assert ft.GEnum.GE1.custom_value() == 11
    assert ft.NSGCEnum.NSGE2.custom_value() == 12


def test_enum_strip_prefix():
    # 1 isn't a valid identifier, so it's not stripped
    assert ft.StripPrefixEnum.STRIP_1 == 1
    # STRIP_B is converted to B
    assert ft.StripPrefixEnum.B == 2


def test_enum_math():
    assert ft.GEnumMath.MGE1 & 1 == 1
    assert ft.EnumContainer2.InnerMathEnum.IME1 & 1 == 1

    # Normal enums don't support math
    with pytest.raises(TypeError):
        ft.EnumContainer.InnerEnum.IE1 & 1
