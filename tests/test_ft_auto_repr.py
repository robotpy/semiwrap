import pytest

from swtest.ft import _ft as ft


def test_reading_repr_uses_current_python_values():
    reading = ft.Reading()
    reading.channel, reading.value, reading.valid = 2, 3.5, True
    assert repr(reading) == "Reading(channel=2, value=3.5, valid=True)"
    reading.value = -1.0
    assert repr(reading) == "Reading(channel=2, value=-1.0, valid=True)"


def test_public_field_class_repr():
    assert repr(ft.ReprClass()) == "ReprClass(value=4)"


def test_repr_uses_python_names_and_declaration_order():
    obj = ft.ReprNamed()
    obj.text = "line\n'quoted'"
    assert repr(obj) == "ReprNamed(start=1, text=\"line\\n'quoted'\", last=True)"


def test_repr_uses_nested_and_container_python_representations():
    assert repr(ft.ReprNested()) == (
        "ReprNested(reading=Reading(channel=2, value=3.5, valid=True), values=[1, 2])"
    )


def test_repr_omits_array_that_cannot_be_wrapped():
    obj = ft.ReprArray()
    assert not hasattr(obj, "samples")
    assert repr(obj) == "ReprArray(value=1)"


def test_empty_repr():
    assert repr(ft.ReprEmpty()) == "ReprEmpty()"


@pytest.mark.parametrize(
    "name",
    [
        "ReprDisabled",
        "ReprMethod",
        "ReprConstructor",
        "ReprDestructor",
        "ReprDerived",
        "ReprPrivate",
    ],
)
def test_disabled_or_ineligible_class_has_no_generated_repr(name):
    assert "__repr__" not in getattr(ft, name).__dict__


@pytest.mark.parametrize(
    "name,expected",
    [
        ("ReprCustom", "custom repr"),
        ("ReprGlobalCustom", "global custom repr"),
        ("ReprCustomInt", "template custom repr"),
    ],
)
def test_custom_repr_is_preserved(name, expected):
    assert repr(getattr(ft, name)()) == expected


def test_template_repr_uses_instance_name():
    assert repr(ft.ReprInt()) == "ReprInt(value=0)"
    assert repr(ft.ReprString()) == "ReprString(value='')"


def test_nested_class_repr_uses_qualified_python_name():
    assert repr(ft.ReprOuter.Inner()) == "ReprOuter.Inner(value=5)"


def test_recursive_repr_is_guarded():
    node = ft.ReprNode()
    node.next = node
    assert repr(node) == "ReprNode(next=...)"
    node.next = None
    assert repr(node) == "ReprNode(next=None)"


def test_python_subclass_repr_uses_python_values_and_recovers_from_errors():
    class ReadingSubclass(ft.Reading):
        @property
        def channel(self):
            if self.fail:
                raise ValueError("cannot read channel")
            return "subclass channel"

    obj = ReadingSubclass()
    obj.value, obj.valid = 3.5, True
    obj.fail = True
    with pytest.raises(ValueError, match="cannot read channel"):
        repr(obj)
    obj.fail = False
    assert repr(obj) == (
        f"{ReadingSubclass.__qualname__}"
        "(channel='subclass channel', value=3.5, valid=True)"
    )
