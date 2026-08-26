from swtest.ft import _ft
from swtest.ft._ft import subpkg


def test_sp_func():
    subpkg.sp_func


def test_sp2_func():
    subpkg.sp2_func


def test_sp_class():
    subpkg.SPClass


def test_subpackage_class_inline_code_has_root_module():
    assert _ft.class_inline_code_module_name == "swtest.ft._ft"
    assert not hasattr(subpkg, "class_inline_code_module_name")


def test_subpackage_enum_inline_code_has_root_module():
    assert _ft.enum_inline_code_module_name == "swtest.ft._ft"
    assert not hasattr(subpkg, "enum_inline_code_module_name")


def test_sp2_class():
    subpkg.SP2Class


def test_sp_template():
    subpkg.SPTemplate


def test_sp2_template():
    subpkg.SP2Template
