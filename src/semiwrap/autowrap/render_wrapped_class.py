from . import render_pybind11 as rpybind11
from .buffer import RenderBuffer
from .context import ClassContext
from .namespace_utils import namespace_scope, normalize_namespace


def class_helper_name(cls: ClassContext) -> str:
    return f"semiwrap_bind_{cls.full_cpp_name_identifier}"


def class_helper_qualname(cls: ClassContext) -> str:
    name = class_helper_name(cls)
    namespace = normalize_namespace(cls.namespace)
    return f"{namespace}::{name}" if namespace else name


def class_scope_exports_name(cls: ClassContext) -> str:
    return f"{class_helper_name(cls)}_scope_exports"


def class_scope_exports_qualname(cls: ClassContext) -> str:
    name = class_scope_exports_name(cls)
    namespace = normalize_namespace(cls.namespace)
    return f"{namespace}::{name}" if namespace else name


def has_class_scope_exports(cls: ClassContext) -> bool:
    return bool(cls.user_typealias or cls.constants)


def render_class_helper(r: RenderBuffer, cls: ClassContext) -> None:
    helper_name = class_helper_name(cls)
    with namespace_scope(r, cls.namespace, anonymous=True):
        # A separate carrier lets the coordinator inherit aliases (including
        # alias templates) and constants without repeating their expressions.
        if has_class_scope_exports(cls):
            exports_name = class_scope_exports_name(cls)
            r.writeln(f"struct {exports_name} {{")
            with r.indent():
                rpybind11.cls_user_using(r, cls)
                rpybind11.cls_consts(r, cls)
            r.writeln(f"}}; // struct {exports_name}\n")
            r.writeln(f"struct {helper_name} : {exports_name} {{")
        else:
            r.writeln(f"struct {helper_name} {{")
        with r.indent():
            rpybind11.cls_decl(r, cls)
            r.writeln("\npy::module &m;")
            r.writeln("py::handle scope;")
            r.writeln(f"\nexplicit {helper_name}(py::module &m, py::handle scope) :")
            with r.indent():
                rpybind11.cls_init(r, cls, f'"{cls.py_name}"', "scope")
                r.writeln("m(m),")
                r.writeln("scope(scope)")
            r.writeln("{}")
            r.writeln("\nvoid define_enums() {")
            with r.indent():
                rpybind11.cls_def_enum(r, cls, cls.var_name)
                for child in cls.child_classes:
                    rpybind11.cls_def_enum(r, child, child.var_name)
            r.writeln("}")
            r.writeln("\nvoid finish() {")
            with r.indent():
                rpybind11.cls_auto_using(r, cls)
                rpybind11.cls_def(r, cls, cls.var_name)
            r.writeln("}")
        r.writeln(f"}}; // struct {helper_name}")
