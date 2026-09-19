import pytest

from swtest.ft import _ft as ft


@pytest.fixture(params=["function", "method"])
def overloads(request):
    if request.param == "function":
        return (
            ft.bindingOrderUnchanged,
            ft.bindingOrderLater,
            ft.bindingOrderTied,
            ft.bindingOrderInherited,
        )
    obj = ft.BindingOrder(42)
    return obj.unchanged, obj.later, obj.tied, obj.inherited


def test_binding_order_defaults_preserve_declaration_order(overloads):
    unchanged, _, _, _ = overloads
    assert unchanged(42) == 1


def test_positive_binding_order_moves_overload_later(overloads):
    _, later, _, _ = overloads
    assert later(42) == 2


def test_equal_priorities_preserve_declaration_order(overloads):
    _, _, tied, _ = overloads
    # The second and third overloads have the same negative priority.
    assert tied(42) == 2
    # Exclude the second overload: the third still precedes the first.
    assert tied(42, skip=0) == 3


def test_binding_order_inheritance_and_explicit_zero(overloads):
    _, _, _, inherited = overloads
    assert inherited(42) == 4  # Explicit -1 precedes explicit 0 and inherited 2.
    # Exclude the fourth overload: explicit 0 overrides the inherited 2.
    assert inherited(42, subset=0) == 3
    # Exclude both overrides: equal inherited priorities retain original order.
    assert inherited(42, inherited=0) == 1


def test_template_method_binding_order():
    assert ft.BindingOrderTemplateInt().choose(42) == 2


def test_equal_priorities_preserve_public_before_protected_order():
    # The protected overload is declared first, but public bindings came first
    # before binding_order was introduced. Both are renamed to the same Python
    # name so this tests actual overload resolution across the access boundary.
    assert ft.BindingOrder(42).mixedUnchanged(42) == 1


def test_protected_overload_can_precede_public_overload():
    assert ft.BindingOrder(42).mixedPrioritized(42) == 2
