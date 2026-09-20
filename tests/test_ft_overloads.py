from swtest.ft import _ft as ft


def test_binding_order_resolves_ambiguous_overloads():
    assert ft.bindingOrder(42) == 2
    obj = ft.BindingOrder(42)
    assert obj.selected == 2
    assert obj.choose(42) == 2
    assert obj.chooseStatic(42) == 2
    assert obj._chooseProtected(42) == 2
    assert obj.unchanged(42) == 1


def test_fn_overloads():
    assert ft.fnOverload(1) == 1
    assert ft.fnOverload(1, 2) == 2


def test_cls_overloads():
    oo = ft.OverloadedObject()
    assert oo.overloaded(1) == 0x1
    assert oo.overloaded("bob") == 0x2

    assert oo.overloaded_constexpr(1, 2) == 3
    assert oo.overloaded_constexpr(1, 2, 3) == 6

    assert ft.OverloadedObject.overloaded_static(1) == 0x3
    assert ft.OverloadedObject.overloaded_static("yup") == 0x4
