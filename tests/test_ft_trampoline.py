from swtest_base._module import abaseclass
from swtest.ft._ft import (
    ClassWithTrampoline,
    ConstexprTrampoline,
    NamespacedRemoteTrampoline,
    RemoteTrampoline,
)


def test_class_with_trampoline():
    c = ClassWithTrampoline()
    assert c.get42() == 42
    assert c.get43() == 43

    assert c.fnWithMoveOnlyParam(4) == 4
    assert ClassWithTrampoline.check_moveonly(c) == 7


def test_trampoline_with_mv():
    class PyClassWithTrampoline(ClassWithTrampoline):
        pass

    c = PyClassWithTrampoline()
    assert ClassWithTrampoline.check_moveonly(c) == 7


def test_trampoline_without_mv():
    class PyClassWithTrampoline(ClassWithTrampoline):
        def fnWithMoveOnlyParam(self, i):
            assert i == 7
            return 8

    c = PyClassWithTrampoline()
    assert ClassWithTrampoline.check_moveonly(c) == 8


def test_constexpr_trampoline():
    ConstexprTrampoline()


def test_remote_trampoline():
    a = abaseclass()
    assert a.fn() == "abaseclass"

    r = RemoteTrampoline()
    assert r.fn() == "RemoteTrampoline"

    assert isinstance(r, abaseclass)


def test_namespaced_remote_trampoline_with_global_base():
    r = NamespacedRemoteTrampoline()
    assert r.fn() == "NamespacedRemoteTrampoline"
    assert isinstance(r, abaseclass)
