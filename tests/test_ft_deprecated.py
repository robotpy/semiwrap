import warnings

import pytest

from swtest import ft


def test_deprecated_fn():
    with pytest.warns(DeprecationWarning, match="use fnNotDeprecated instead"):
        assert ft._ft.fnDeprecated() == 1


def test_not_deprecated_fn():
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        assert ft._ft.fnNotDeprecated() == 2


def test_deprecated_fn_multi_literal():
    with pytest.warns(DeprecationWarning, match="multiple literals"):
        assert ft._ft.fnDeprecatedMultiLiteral() == 3


def test_deprecated_fn_no_message():
    with pytest.warns(DeprecationWarning, match="fnDeprecatedNoMessage is deprecated"):
        assert ft._ft.fnDeprecatedNoMessage() == 4


def test_deprecated_fn_as_error():
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        with pytest.raises(DeprecationWarning, match="use fnNotDeprecated instead"):
            ft._ft.fnDeprecated()


def test_deprecated_constructor():
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        ft._ft.DeprecatedMembers()

    with pytest.warns(DeprecationWarning, match="deprecated constructor"):
        m = ft._ft.DeprecatedMembers(3)
    assert m.notDeprecatedField == 3


def test_deprecated_methods():
    m = ft._ft.DeprecatedMembers()

    with pytest.warns(DeprecationWarning, match="deprecated method"):
        assert m.deprecatedMethod() == 5

    with pytest.warns(DeprecationWarning, match="deprecated static method"):
        assert ft._ft.DeprecatedMembers.deprecatedStaticMethod() == 6


def test_deprecated_overload():
    m = ft._ft.DeprecatedMembers()

    with warnings.catch_warnings():
        warnings.simplefilter("error")
        assert m.overloaded(1) == 1

    with pytest.warns(DeprecationWarning, match="deprecated overload"):
        assert m.overloaded(1.5) == 2


def test_deprecated_virtual():
    m = ft._ft.DeprecatedMembers()
    with pytest.warns(DeprecationWarning, match="deprecated virtual"):
        assert m.deprecatedVirtual() == 7
    assert m.callDeprecatedVirtual() == 7

    class Child(ft._ft.DeprecatedMembers):
        def deprecatedVirtual(self):
            return 42

    c = Child()
    assert c.callDeprecatedVirtual() == 42


def test_deprecated_field():
    m = ft._ft.DeprecatedField()
    m.deprecatedField = 9
    assert m.deprecatedField == 9
