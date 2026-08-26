from swtest import ft
from swtest.ft import _ft


def test_basic_template():
    """template/basic.h"""
    s = ft.TBasicString()

    s.setT("string")
    assert s.t == "string"
    assert s.getT() == "string"


def test_cross_package_template_binder():
    value = _ft.RemoteTemplateInt(42)
    assert value.get() == 42


def test_cross_package_nested_template_binder():
    value = _ft.ProviderNestedInt(43)
    assert value.get() == 43


def test_dependent_using():
    du = ft.TDependentUsingInt()
    assert du.getThird([1, 2, 3]) == 3


def test_dependent_using2():
    du = ft.TDependentUsing2Int()
    assert du.getThird([1, 2, 3]) == 3


def test_classwithfn():
    assert ft.TClassWithFn.getT(1) == 1
    assert ft.TClassWithFn.getT(False) is False


def test_nested_template():
    """template/nested.h"""
    i = ft.TOuter.Inner()
    assert type(i.t) == int

    assert repr(i) == "TOuter.Inner()"


def test_local_nested_template_binder():
    value = _ft.LocalNestedInt(44)
    assert value.get() == 44


def test_nested_template_beneath_templated_class():
    value = _ft.NestedTemplateIntDouble(45, 4.5)
    assert value.outer == 45
    assert value.inner == 4.5

    value.outer = 46
    value.inner = 5.5
    assert value.getOuter() == 46
    assert value.getInner() == 5.5


def test_numeric():
    """template/numeric.h"""
    b4 = ft.TBaseGetN4()
    assert b4.getIt() == 4

    b6 = ft.TBaseGetN6()
    assert b6.getIt() == 6

    c4 = ft.TChildGetN4()
    assert c4.getIt() == 4

    c6 = ft.TChildGetN6()
    assert c6.getIt() == 6


#
# CRTP handling tests
#


def test_crtp_base():
    b = ft.TBase()
    assert b.baseFn() == 42
    assert b.get() == "TBase"


def test_crtp_concrete():
    c = ft.TConcrete()
    assert c.concrete() == 32
    assert c.baseFn() == 42
    assert c.get() == "TCrtp"


#
# Template base weirdness
#


def test_tvbase2():
    p = ft.TVParam2()
    assert p.get() == 2

    b = ft.TVBase2()
    assert b.get(p) == "TVBase 2"

    c = ft.TVChild2()
    assert c.get(p) == "TVChild 2"
