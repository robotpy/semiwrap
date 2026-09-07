import inspect

import swtest.ft as ft


def warning(message: str) -> str:
    return f".. warning::\n   Deprecated: {message}"


def test_deprecated_free_function_docs_and_calls():
    module = ft._ft

    assert module.deprecated_without_message() == 1
    assert ".. warning::\n   Deprecated." in inspect.getdoc(
        module.deprecated_without_message
    )

    assert module.deprecated_free_function() == 2
    assert warning("Use current_free_function().") in inspect.getdoc(
        module.deprecated_free_function
    )

    assert module.deprecated_documented_function() == 3
    documented_doc = inspect.getdoc(module.deprecated_documented_function)
    documented_warning = warning("Use current_documented_function().")
    assert documented_warning in documented_doc
    assert documented_doc.count("Use current_documented_function().") == 1


def test_deprecated_member_docs_and_calls():
    cls = ft._ft.DeprecatedMembers
    value = cls()
    other = cls()

    assert warning("Use DeprecatedMembers::create().") in inspect.getdoc(cls.__init__)
    assert value.deprecated_method() == 4
    assert warning("Use current_method().") in inspect.getdoc(cls.deprecated_method)
    assert cls.deprecated_static_method() == 5
    assert warning("Use current_static_method().") in inspect.getdoc(
        cls.deprecated_static_method
    )

    assert value == value
    assert value != other
    assert warning("Use operator!=().") in inspect.getdoc(cls.__eq__)

    value.deprecated_field = 6
    assert value.deprecated_field == 6
    assert warning("Use current_field.") in inspect.getdoc(
        inspect.getattr_static(cls, "deprecated_field")
    )

    assert cls.deprecated_static_field == 7
    assert warning("Use current_static_field.") in inspect.getdoc(
        inspect.getattr_static(cls, "deprecated_static_field")
    )


def test_deprecated_class_and_template_docs_and_calls():
    deprecated_class = ft._ft.DeprecatedClass
    assert callable(deprecated_class)
    assert deprecated_class().value() == 8
    assert warning("Use CurrentClass.") in inspect.getdoc(deprecated_class)

    deprecated_template = ft._ft.DeprecatedTemplateInt
    assert callable(deprecated_template)
    assert deprecated_template().get() == 15
    assert warning("Use CurrentTemplate.") in inspect.getdoc(deprecated_template)


def test_deprecated_enum_and_value_docs_are_readable():
    deprecated_enum = ft._ft.DeprecatedEnum
    assert deprecated_enum.Value.value == 9
    assert warning("Use CurrentEnum.") in inspect.getdoc(deprecated_enum)
    assert warning("Use CurrentEnum.") in inspect.getdoc(deprecated_enum.Value)

    mixed_enum = ft._ft.MixedDeprecatedEnum
    assert mixed_enum.DeprecatedValue.value == 10
    assert mixed_enum.CurrentValue.value == 11
    deprecated_value_doc = inspect.getdoc(mixed_enum.DeprecatedValue)
    assert ".. warning::" in deprecated_value_doc
    assert "Deprecated: Use MixedDeprecatedEnum::CurrentValue." in deprecated_value_doc


def test_deprecated_virtual_trampoline_member_docs_are_readable():
    cls = ft._ft.DeprecatedVirtual
    assert callable(cls.deprecated_virtual)
    assert warning("Use current_virtual().") in inspect.getdoc(cls.deprecated_virtual)
    assert callable(cls._deprecated_protected_method)
    assert warning("Use current_protected_method().") in inspect.getdoc(
        cls._deprecated_protected_method
    )
    assert warning("Use current_protected_property.") in inspect.getdoc(
        inspect.getattr_static(cls, "_deprecated_protected_property")
    )
