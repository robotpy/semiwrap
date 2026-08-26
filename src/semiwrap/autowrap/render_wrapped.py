import typing

from .buffer import RenderBuffer
from .context import (
    ClassContext,
    EnumContext,
    FunctionContext,
    HeaderContext,
    TemplateInstanceContext,
)
from .namespace_utils import namespace_scope, normalize_namespace

from . import render_pybind11 as rpybind11
from .render_cls_prologue import render_class_prologue
from .render_wrapped_class import (
    class_helper_qualname,
    class_scope_exports_qualname,
    has_class_scope_exports,
    render_class_helper,
)


def _class_helper_var_name(cls: ClassContext) -> str:
    return f"semiwrap_helper_{cls.full_cpp_name_identifier}"


def _absolute_qualname(qualname: str) -> str:
    return qualname if qualname.startswith("::") else f"::{qualname}"


def _enum_helper_name(hctx: HeaderContext, index: int) -> str:
    return f"semiwrap_enum_{hctx.hname}_{index}"


def _enum_helper_qualname(hctx: HeaderContext, enum: EnumContext, index: int) -> str:
    helper_name = _enum_helper_name(hctx, index)
    namespace = normalize_namespace(enum.namespace)
    return f"{namespace}::{helper_name}" if namespace else helper_name


def _render_enum_helper(
    r: RenderBuffer,
    hctx: HeaderContext,
    enum: EnumContext,
    index: int,
) -> None:
    helper_name = _enum_helper_name(hctx, index)
    with namespace_scope(r, enum.namespace, anonymous=True):
        r.writeln(f"struct {helper_name} {{")
        with r.indent():
            r.writeln("py::module &m;")
            rpybind11.enum_decl(r, enum, "value")
            r.writeln(f"{helper_name}(py::module &m, py::module &scope) :")
            with r.indent():
                r.writeln("m(m),")
                r.writeln(f"value({rpybind11.enum_init_args('scope', enum)})")
            r.writeln("{}")
            r.writeln("void finish() {")
            with r.indent():
                # enum_def emits fluent suffixes, so provide their receiver here.
                r.writeln("value")
                with r.indent():
                    rpybind11.enum_def(r, "value", enum)
            r.writeln("}")
        r.writeln(f"}}; // struct {helper_name}")


def _function_helper_name(hctx: HeaderContext, index: int) -> str:
    return f"semiwrap_function_{hctx.hname}_{index}"


def _function_helper_qualname(
    hctx: HeaderContext, fn: FunctionContext, index: int
) -> str:
    helper_name = _function_helper_name(hctx, index)
    namespace = normalize_namespace(fn.namespace)
    return f"{namespace}::{helper_name}" if namespace else helper_name


def _render_function_helper(
    r: RenderBuffer,
    hctx: HeaderContext,
    fn: FunctionContext,
    index: int,
) -> None:
    helper_name = _function_helper_name(hctx, index)
    with namespace_scope(r, fn.namespace, anonymous=True):
        r.writeln(f"void {helper_name}(py::module &scope) {{")
        with r.indent():
            rpybind11.genmethod(r, "scope", None, fn, None)
        r.writeln("}")


def _render_class_access_decls(
    r: RenderBuffer, helper_cls: ClassContext, cls: ClassContext
) -> None:
    if cls.template is not None:
        return

    helper_var = _class_helper_var_name(helper_cls)
    r.writeln(f"decltype({helper_var}.{cls.var_name}) &{cls.var_name};")
    if cls.trampoline is not None:
        r.writeln(
            f"using {cls.trampoline.var} = "
            f"{_absolute_qualname(class_helper_qualname(helper_cls))}"
            f"::{cls.trampoline.var};"
        )

    for child in cls.child_classes:
        _render_class_access_decls(r, helper_cls, child)


def _template_instances(
    cls: ClassContext,
) -> typing.Iterator[TemplateInstanceContext]:
    if cls.template is not None:
        yield from cls.template.instances
    for child in cls.child_classes:
        yield from _template_instances(child)


def _resolve_inline_code_namespace(hctx: HeaderContext) -> str:
    if not hctx.inline_code:
        return ""
    if hctx.inline_code_namespace is not None:
        return normalize_namespace(hctx.inline_code_namespace)

    namespaces = {normalize_namespace(enum.namespace) for enum in hctx.enums}
    namespaces.update(normalize_namespace(cls.namespace) for cls in hctx.classes)
    namespaces.update(
        normalize_namespace(template.namespace) for template in hctx.template_instances
    )
    namespaces.update(
        normalize_namespace(fn.namespace) for fn in hctx.functions if not fn.ignore_py
    )
    if len(namespaces) > 1:
        formatted = ", ".join(repr(namespace) for namespace in sorted(namespaces))
        raise ValueError(
            f"{hctx.orig_yaml}: inline_code has multiple target namespaces "
            f"({formatted}); specify inline_code_namespace"
        )
    return next(iter(namespaces), "")


def _render_class_access_inits(
    r: RenderBuffer, helper_cls: ClassContext, cls: ClassContext
) -> None:
    if cls.template is not None:
        return

    helper_var = _class_helper_var_name(helper_cls)
    r.writeln(f"{cls.var_name}({helper_var}.{cls.var_name}),")
    for child in cls.child_classes:
        _render_class_access_inits(r, helper_cls, child)


def render_wrapped_cpp(hctx: HeaderContext) -> str:
    """
    This contains the primary binding code generated from parsing a single
    header file. There are also per-class headers generated (templates,
    trampolines), and those are included/used by this.
    """
    r = RenderBuffer()

    render_class_prologue(r, hctx)

    if hctx.template_instances:
        r.writeln(f'\n#include "{hctx.hname}_tmpl.hpp"')

    if hctx.extra_includes:
        r.writeln()
        for inc in hctx.extra_includes:
            r.writeln(f"#include <{inc}>")

    if hctx.user_typealias:
        r.writeln()
        for typealias in hctx.user_typealias:
            r.writeln(f"{typealias};")

    #
    # Ordering of the initialization function
    #
    # - namespace/typealiases
    # - global enums
    # - templates (because CRTP)
    # - class declarations
    # - class enums
    # - class methods
    # - global methods
    #
    # Additionally, we use two-part initialization to ensure that documentation
    # strings are generated properly. First part is to register the class with
    # pybind11, second part is to generate all the methods/etc for it.
    #
    # TODO: make type_traits optional by detecting trampoline

    r.writeln("\n#include <type_traits>")

    for index, enum in enumerate(hctx.enums, start=1):
        r.writeln()
        _render_enum_helper(r, hctx, enum, index)

    for cls in hctx.classes:
        if cls.template is None:
            r.writeln()
            render_class_helper(r, cls)

    for index, fn in enumerate(hctx.functions, start=1):
        if not fn.ignore_py:
            r.writeln()
            _render_function_helper(r, hctx, fn, index)

    r.writeln()
    coordinator_name = f"semiwrap_{hctx.hname}_initializer"
    coordinator_namespace = _resolve_inline_code_namespace(hctx)
    coordinator_qualname = (
        f"{coordinator_namespace}::{coordinator_name}"
        if coordinator_namespace
        else coordinator_name
    )
    with namespace_scope(r, coordinator_namespace, anonymous=True):
        exports = [
            _absolute_qualname(class_scope_exports_qualname(cls))
            for cls in hctx.classes
            if cls.template is None and has_class_scope_exports(cls)
        ]
        if exports:
            r.writeln(f"struct {coordinator_name} :")
            with r.indent():
                for index, exports_name in enumerate(exports):
                    comma = "," if index != len(exports) - 1 else ""
                    r.writeln(f"{exports_name}{comma}")
            r.writeln("{\n")
        else:
            r.writeln(f"struct {coordinator_name} {{\n")

        with r.indent():
            if hctx.subpackages:
                for vname in hctx.subpackages.values():
                    r.writeln(f"py::module {vname};")

            # enums
            for index, enum in enumerate(hctx.enums, start=1):
                r.writeln(
                    f"{_absolute_qualname(_enum_helper_qualname(hctx, enum, index))} "
                    f"enum{index};"
                )

            # template decls
            for tmpl_data in hctx.template_instances:
                if not tmpl_data.matched:
                    r.writeln(
                        f"{_absolute_qualname(tmpl_data.binder_full_cpp_name)} "
                        f"{tmpl_data.var_name};"
                    )

            # class decls
            for cls in hctx.classes:
                if cls.template is None:
                    r.writeln()
                    r.writeln(
                        f"{_absolute_qualname(class_helper_qualname(cls))} "
                        f"{_class_helper_var_name(cls)};"
                    )
                    _render_class_access_decls(r, cls, cls)
                for tmpl_data in _template_instances(cls):
                    r.writeln(
                        f"{_absolute_qualname(tmpl_data.binder_full_cpp_name)} "
                        f"{tmpl_data.var_name};"
                    )

            r.writeln("\npy::module &m;\n")
            r.writeln(f"{coordinator_name}(py::module &m) :")

            with r.indent():
                for pkg, vname in hctx.subpackages.items():
                    r.writeln(f'{vname}(m.def_submodule("{pkg}")),')

                for index, enum in enumerate(hctx.enums, start=1):
                    r.writeln(f"enum{index}(m, {enum.scope_var}),")

                for tmpl_data in hctx.template_instances:
                    if not tmpl_data.matched:
                        r.writeln(
                            f'{tmpl_data.var_name}({tmpl_data.scope_var}, "{tmpl_data.py_name}"),'
                        )

                for cls in hctx.classes:
                    if cls.template is None:
                        r.writeln(f"{_class_helper_var_name(cls)}(m, {cls.scope_var}),")
                        _render_class_access_inits(r, cls, cls)
                    for tmpl_data in _template_instances(cls):
                        r.writeln(
                            f'{tmpl_data.var_name}({tmpl_data.scope_var}, "{tmpl_data.py_name}"),'
                        )

                r.writeln("m(m)")

            if hctx.enums or hctx.classes:
                r.writeln("{")
                with r.indent():
                    # enums can go in the initializer because they cant have dependencies,
                    # and then we dont need to figure out class dependencies for enum arguments

                    for index, enum in enumerate(hctx.enums, start=1):
                        r.writeln(f"enum{index}.finish();")

                    for cls in hctx.classes:
                        if cls.template is None:
                            r.writeln(f"{_class_helper_var_name(cls)}.define_enums();")
                r.writeln("}")
            else:
                r.writeln("{}")

            r.writeln("\nvoid finish() {\n")

            with r.indent():
                # Templates
                for tdata in hctx.template_instances:
                    r.writeln(f"\n{tdata.var_name}.finish(")
                    with r.indent():
                        if tdata.doc_set:
                            r.writeln(f'{rpybind11.mkdoc("", tdata.doc_set, "")},')
                        else:
                            r.writeln("nullptr,")

                        if tdata.doc_add:
                            r.writeln(rpybind11.mkdoc("", tdata.doc_add, ""))
                        else:
                            r.writeln("nullptr")
                    r.writeln(");")

                # Class methods
                for cls in hctx.classes:
                    if cls.template is None:
                        r.writeln(f"{_class_helper_var_name(cls)}.finish();")

                # Global methods
                if hctx.functions:
                    r.writeln()
                    for index, fn in enumerate(hctx.functions, start=1):
                        if not fn.ignore_py:
                            r.writeln(
                                f"{_absolute_qualname(_function_helper_qualname(hctx, fn, index))}"
                                f"({fn.scope_var});"
                            )

                if hctx.inline_code:
                    r.writeln()
                    r.write_trim(hctx.inline_code)

            r.writeln("}")

        r.writeln(f"}}; // struct {coordinator_name}\n")

    r.writeln()
    with namespace_scope(r, "", anonymous=True):
        r.writeln(f"static std::unique_ptr<{coordinator_qualname}> cls;")

    r.writeln(
        "\n"
        f"void begin_init_{hctx.hname}(py::module &m) {{\n"
        f"  cls = std::make_unique<{coordinator_qualname}>(m);\n"
        "}\n"
        "\n"
        f"void finish_init_{hctx.hname}() {{\n"
        "  cls->finish();\n"
        "  cls.reset();\n"
        "}\n"
    )

    return r.getvalue()
