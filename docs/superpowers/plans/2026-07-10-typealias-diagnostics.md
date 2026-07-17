# Typealias Diagnostics Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Generate fail-fast compile-time alias probes that make missing semiwrap YAML `typealias` entries fail at a clear generated line.

**Architecture:** Add a small probe collection/rendering helper, store collected probe targets on header/class contexts, and emit probes before generated `.cpp` binding code and trampoline `.hpp` code uses those types. Collection is best-effort and based on parsed C++ types that semiwrap already processes for function signatures.

**Tech Stack:** Python 3, cxxheaderparser type nodes, semiwrap autowrap dataclasses/renderers, pytest, existing C++ fixture project under `tests/cpp/sw-test`.

## Global Constraints

- Diagnostic must be compile-time only in generated C++; do not add generation-time missing-name errors.
- Do not use placeholder C++ declarations for missing types.
- Do not use unconditional `#warning` or `#pragma message` diagnostics.
- Probes must compile away as harmless `using` aliases when candidate types are already visible.
- Generated probe names must be unique, deterministic, and descriptive enough to mention `typealias` and YAML.
- Generated probe `using` lines must be sorted by probe target within each generated C++ scope.
- Emit probes in generated `.cpp` binding scope and generated trampoline `.hpp` class scope where applicable.

---

## File Structure

- Create `src/semiwrap/autowrap/typealias_probe.py`
  - Owns candidate extraction from cxxheaderparser type nodes.
  - Owns deterministic/safe generated alias-name construction.
  - Owns sorted C++ rendering of probe comments and `using` lines.
- Modify `src/semiwrap/autowrap/context.py`
  - Add `typealias_probes: List[str]` to `ClassContext` and `HeaderContext`.
- Modify `src/semiwrap/autowrap/cxxparser.py`
  - Collect probes from return/parameter parsed types while building `FunctionContext`.
  - Add global function probes to `HeaderContext.typealias_probes`.
  - Add class method/constructor probes to `ClassContext.typealias_probes`.
- Modify `src/semiwrap/autowrap/render_wrapped.py`
  - Emit header-level probes in the generated `.cpp` after user header-level `typealias` lines and before initializer struct/class declarations.
- Modify `src/semiwrap/autowrap/render_pybind11.py`
  - Emit class-level probes near existing class user/auto using helpers before class declarations/definitions that use method signatures.
- Modify `src/semiwrap/autowrap/render_cls_trampoline_hpp.py`
  - Emit class-level probes inside generated trampoline classes before constructors and virtual/protected methods.
- Create `tests/test_typealias_probe.py`
  - Unit tests for helper extraction, de-duplication, sanitization, and rendering.
- Modify `tests/test_ft_misc.py`
  - Add generated-output assertions for the existing `using.h` fixture after the C++ project has been built by the test harness.

---

### Task 1: Add typealias probe helper and unit tests

**Files:**
- Create: `src/semiwrap/autowrap/typealias_probe.py`
- Test: `tests/test_typealias_probe.py`

**Interfaces:**
- Consumes: cxxheaderparser `DecoratedType`, `FunctionType`, `NameSpecifier`, `Type`, `Pointer`, `Reference`, `MoveReference`, `Array`, and `TemplateArgument` nodes.
- Produces:
  - `collect_typealias_probes(dt: DecoratedType | FunctionType | None) -> list[str]`
  - `add_typealias_probe(probes: list[str], target: str) -> None`
  - `probe_alias_name(target: str) -> str`
  - `render_typealias_probes(r: RenderBuffer, probes: Sequence[str], *, indent: str = "") -> None`

- [ ] **Step 1: Write failing helper tests**

Create `tests/test_typealias_probe.py` with:

```python
from cxxheaderparser.simple import parse_typename

from semiwrap.autowrap.buffer import RenderBuffer
from semiwrap.autowrap.typealias_probe import (
    add_typealias_probe,
    collect_typealias_probes,
    probe_alias_name,
    render_typealias_probes,
)


def probes_for(type_text: str) -> list[str]:
    return collect_typealias_probes(parse_typename(type_text))


def test_collects_unqualified_alias_from_decorated_type():
    assert probes_for("const CantResolve&") == ["CantResolve"]


def test_collects_template_alias_and_inner_alias_sorted():
    assert probes_for("fancy_list<CantResolve>") == [
        "CantResolve",
        "fancy_list<CantResolve>",
    ]


def test_skips_builtin_std_and_global_root_targets_but_collects_template_args():
    assert probes_for("int") == []
    assert probes_for("std::vector<CantResolve>") == ["CantResolve"]
    assert probes_for("::AlreadyQualified") == []


def test_add_typealias_probe_deduplicates_and_sorts():
    probes: list[str] = []
    add_typealias_probe(probes, "CantResolve")
    add_typealias_probe(probes, "AlsoCantResolve")
    add_typealias_probe(probes, "CantResolve")
    assert probes == ["AlsoCantResolve", "CantResolve"]


def test_probe_alias_name_is_deterministic_and_descriptive():
    assert probe_alias_name("CantResolve") == (
        "semiwrap_typealias_probe_CantResolve__add_typealias_to_yaml"
    )
    assert probe_alias_name("fancy_list<CantResolve>") == (
        "semiwrap_typealias_probe_fancy_list_CantResolve__add_typealias_to_yaml"
    )


def test_render_typealias_probes_emits_comment_and_sorted_using_lines():
    r = RenderBuffer()
    render_typealias_probes(r, ["CantResolve", "AlsoCantResolve"])
    out = r.getvalue()
    assert "semiwrap diagnostic" in out
    assert "add a typealias entry" in out
    assert out.index(
        "using semiwrap_typealias_probe_AlsoCantResolve__add_typealias_to_yaml"
    ) < out.index("using semiwrap_typealias_probe_CantResolve__add_typealias_to_yaml")
    assert (
        "using semiwrap_typealias_probe_CantResolve__add_typealias_to_yaml "
        "[[maybe_unused]] = CantResolve;"
    ) in out
```

- [ ] **Step 2: Run helper tests and verify they fail**

Run:

```bash
pytest tests/test_typealias_probe.py -q
```

Expected: FAIL during import with `ModuleNotFoundError: No module named 'semiwrap.autowrap.typealias_probe'`.

- [ ] **Step 3: Implement helper module**

Create `src/semiwrap/autowrap/typealias_probe.py` with:

```python
import re
import typing as T

from cxxheaderparser.types import (
    Array,
    DecoratedType,
    FunctionType,
    FundamentalSpecifier,
    MoveReference,
    NameSpecifier,
    Pointer,
    Reference,
    TemplateArgument,
    Type,
    Value,
)

from .buffer import RenderBuffer

_INT_TYPES = frozenset(
    [
        "bool",
        "char",
        "char8_t",
        "char16_t",
        "char32_t",
        "double",
        "float",
        "int",
        "long",
        "short",
        "signed",
        "unsigned",
        "void",
        "wchar_t",
        "size_t",
        "ssize_t",
        "ptrdiff_t",
        "intmax_t",
        "uintmax_t",
    ]
    + [
        f"{prefix}{middle}{bits}_t"
        for prefix in ("int", "uint")
        for middle in ("", "_fast", "_least")
        for bits in ("8", "16", "32", "64")
    ]
)

_SANITIZE_RE = re.compile(r"[^0-9A-Za-z]+")


def _is_builtin_type(t: Type) -> bool:
    last = t.typename.segments[-1]
    if isinstance(last, FundamentalSpecifier):
        return True
    if isinstance(last, NameSpecifier) and len(t.typename.segments) == 1:
        return last.name in _INT_TYPES
    return False


def _target_from_type(t: Type) -> str | None:
    if _is_builtin_type(t):
        return None
    if not all(isinstance(seg, NameSpecifier) for seg in t.typename.segments):
        return None

    target = t.typename.format()
    if target.startswith("::"):
        return None
    if target.startswith(("std::", "py::", "pybind11::", "semiwrap::", "swgen::")):
        return None
    return target


def _collect_from_template_args(t: Type, out: list[str]) -> None:
    for segment in t.typename.segments:
        if not isinstance(segment, NameSpecifier) or segment.specialization is None:
            continue
        for arg in segment.specialization.args:
            _collect_from_template_arg(arg, out)


def _collect_from_template_arg(arg: TemplateArgument, out: list[str]) -> None:
    value = arg.arg
    if isinstance(value, Value):
        return
    collect_typealias_probes_into(value, out)


def add_typealias_probe(probes: list[str], target: str) -> None:
    if target and target not in probes:
        probes.append(target)
        probes.sort()


def collect_typealias_probes_into(
    dt: DecoratedType | FunctionType | None, out: list[str]
) -> None:
    if dt is None:
        return
    if isinstance(dt, Type):
        target = _target_from_type(dt)
        if target is not None:
            add_typealias_probe(out, target)
        _collect_from_template_args(dt, out)
    elif isinstance(dt, Pointer):
        collect_typealias_probes_into(dt.ptr_to, out)
    elif isinstance(dt, Reference):
        collect_typealias_probes_into(dt.ref_to, out)
    elif isinstance(dt, MoveReference):
        collect_typealias_probes_into(dt.moveref_to, out)
    elif isinstance(dt, Array):
        collect_typealias_probes_into(dt.array_of, out)
    elif isinstance(dt, FunctionType):
        collect_typealias_probes_into(dt.return_type, out)
        for param in dt.parameters:
            collect_typealias_probes_into(param.type, out)


def collect_typealias_probes(dt: DecoratedType | FunctionType | None) -> list[str]:
    probes: list[str] = []
    collect_typealias_probes_into(dt, probes)
    return probes


def probe_alias_name(target: str) -> str:
    safe = _SANITIZE_RE.sub("_", target).strip("_")
    if not safe:
        safe = "unknown"
    return f"semiwrap_typealias_probe_{safe}__add_typealias_to_yaml"


def render_typealias_probes(
    r: RenderBuffer, probes: T.Sequence[str], *, indent: str = ""
) -> None:
    for target in sorted(probes):
        alias = probe_alias_name(target)
        r.writeln(
            f"{indent}// semiwrap diagnostic: if this line fails because `{target}` "
            "is unknown,"
        )
        r.writeln(
            f"{indent}// add a typealias entry for `{target}` to the semiwrap yaml file."
        )
        r.writeln(f"{indent}using {alias} [[maybe_unused]] = {target};")
```

- [ ] **Step 4: Run helper tests and verify they pass**

Run:

```bash
pytest tests/test_typealias_probe.py -q
```

Expected: PASS, all six tests pass.

- [ ] **Step 5: Commit helper**

```bash
git add src/semiwrap/autowrap/typealias_probe.py tests/test_typealias_probe.py
git commit -m "Add typealias probe helper"
```

---

### Task 2: Collect probes while parsing headers

**Files:**
- Modify: `src/semiwrap/autowrap/context.py`
- Modify: `src/semiwrap/autowrap/cxxparser.py`
- Test: `tests/test_typealias_probe.py`

**Interfaces:**
- Consumes from Task 1:
  - `add_typealias_probe(probes: list[str], target: str) -> None`
  - `collect_typealias_probes(dt: DecoratedType | FunctionType | None) -> list[str]`
- Produces:
  - `ClassContext.typealias_probes: list[str]`
  - `HeaderContext.typealias_probes: list[str]`

- [ ] **Step 1: Add failing parser collection tests**

Append to `tests/test_typealias_probe.py`:

```python
import pathlib

from cxxheaderparser.options import ParserOptions

from semiwrap.autowrap.cxxparser import parse_header
from semiwrap.autowrap.generator_data import GeneratorData
from semiwrap.config.autowrap_yml import AutowrapConfigYaml


def parse_fixture_header(header_name: str, yaml_name: str):
    root = pathlib.Path("tests/cpp/sw-test/src/swtest/ft/include")
    yml = pathlib.Path("tests/cpp/sw-test/semiwrap/ft") / yaml_name
    cfg = AutowrapConfigYaml.from_file(yml)
    return parse_header(
        header_name,
        root / header_name,
        root,
        GeneratorData(cfg, yml),
        ParserOptions(),
        {},
        False,
    )


def test_parse_header_collects_global_function_typealias_probe():
    hctx = parse_fixture_header("using.h", "using.yml")
    assert "AlsoCantResolve" in hctx.typealias_probes


def test_parse_header_collects_class_constructor_typealias_probe():
    hctx = parse_fixture_header("using.h", "using.yml")
    cls = next(c for c in hctx.classes if c.cpp_name == "ProtectedUsing")
    assert "CantResolve" in cls.typealias_probes
```

- [ ] **Step 2: Run parser collection tests and verify they fail**

Run:

```bash
pytest tests/test_typealias_probe.py::test_parse_header_collects_global_function_typealias_probe tests/test_typealias_probe.py::test_parse_header_collects_class_constructor_typealias_probe -q
```

Expected: FAIL with `AttributeError` for missing `typealias_probes` on context objects.

- [ ] **Step 3: Add context fields**

In `src/semiwrap/autowrap/context.py`, add this field to `ClassContext` near `auto_typealias`:

```python
    #: Best-effort C++ type spellings that should be probed before generated
    #: code uses them. These produce clearer compile-time diagnostics when a
    #: YAML typealias entry is missing.
    typealias_probes: typing.List[str] = field(default_factory=list)
```

Add this field to `HeaderContext` near `user_typealias`:

```python
    #: Best-effort C++ type spellings that should be probed before generated
    #: global binding code uses them.
    typealias_probes: typing.List[str] = field(default_factory=list)
```

- [ ] **Step 4: Import helper and collect probes in parser**

In `src/semiwrap/autowrap/cxxparser.py`, add this import near other autowrap imports:

```python
from .typealias_probe import add_typealias_probe, collect_typealias_probes
```

In `AutowrapVisitor.on_function`, after `fctx.namespace = state.user_data` and before `self.hctx.functions.append(fctx)`, add:

```python
        for probe in collect_typealias_probes(fn.return_type):
            add_typealias_probe(self.hctx.typealias_probes, probe)
        for param in fn.parameters:
            for probe in collect_typealias_probes(param.type):
                add_typealias_probe(self.hctx.typealias_probes, probe)
```

In `AutowrapVisitor._on_class_method`, after the call to `self._on_fn_or_method(...)` and before class-specific method attributes are updated, add:

```python
        for probe in collect_typealias_probes(method.return_type):
            add_typealias_probe(cctx.typealias_probes, probe)
        for param in method.parameters:
            for probe in collect_typealias_probes(param.type):
                add_typealias_probe(cctx.typealias_probes, probe)
```

- [ ] **Step 5: Run parser collection tests and verify they pass**

Run:

```bash
pytest tests/test_typealias_probe.py::test_parse_header_collects_global_function_typealias_probe tests/test_typealias_probe.py::test_parse_header_collects_class_constructor_typealias_probe -q
```

Expected: PASS, both tests pass.

- [ ] **Step 6: Run all probe tests**

Run:

```bash
pytest tests/test_typealias_probe.py -q
```

Expected: PASS, all tests in `tests/test_typealias_probe.py` pass.

- [ ] **Step 7: Commit parser collection**

```bash
git add src/semiwrap/autowrap/context.py src/semiwrap/autowrap/cxxparser.py tests/test_typealias_probe.py
git commit -m "Collect typealias probes while parsing"
```

---

### Task 3: Render probes in generated `.cpp` binding code

**Files:**
- Modify: `src/semiwrap/autowrap/render_wrapped.py`
- Modify: `src/semiwrap/autowrap/render_pybind11.py`
- Test: `tests/test_typealias_probe.py`

**Interfaces:**
- Consumes from Task 1:
  - `render_typealias_probes(r: RenderBuffer, probes: Sequence[str], *, indent: str = "") -> None`
- Consumes from Task 2:
  - `HeaderContext.typealias_probes`
  - `ClassContext.typealias_probes`
- Produces generated `.cpp` output containing `semiwrap_typealias_probe_*__add_typealias_to_yaml` aliases.

- [ ] **Step 1: Add failing render tests for `.cpp` output**

Append to `tests/test_typealias_probe.py`:

```python
from semiwrap.autowrap.render_wrapped import render_wrapped_cpp


def test_render_wrapped_cpp_emits_global_typealias_probe_before_initializer():
    hctx = parse_fixture_header("using.h", "using.yml")
    out = render_wrapped_cpp(hctx)
    probe = "semiwrap_typealias_probe_AlsoCantResolve__add_typealias_to_yaml"
    assert probe in out
    assert out.index(probe) < out.index("struct semiwrap_using_initializer")
    assert "using semiwrap_typealias_probe_AlsoCantResolve__add_typealias_to_yaml" in out
    assert "= AlsoCantResolve;" in out


def test_render_wrapped_cpp_emits_class_typealias_probe_inside_initializer():
    hctx = parse_fixture_header("using.h", "using.yml")
    out = render_wrapped_cpp(hctx)
    probe = "semiwrap_typealias_probe_CantResolve__add_typealias_to_yaml"
    assert probe in out
    assert out.index("struct semiwrap_using_initializer") < out.index(probe)
    assert out.index(probe) < out.index("py::class_<typename cr::inner::ProtectedUsing")
```

- [ ] **Step 2: Run render tests and verify they fail**

Run:

```bash
pytest tests/test_typealias_probe.py::test_render_wrapped_cpp_emits_global_typealias_probe_before_initializer tests/test_typealias_probe.py::test_render_wrapped_cpp_emits_class_typealias_probe_inside_initializer -q
```

Expected: FAIL because generated output does not contain `semiwrap_typealias_probe_`.

- [ ] **Step 3: Render header-level probes in `.cpp` output**

In `src/semiwrap/autowrap/render_wrapped.py`, add this import near existing imports:

```python
from .typealias_probe import render_typealias_probes
```

After the existing `if hctx.user_typealias:` block and before the ordering comment, add:

```python
    if hctx.typealias_probes:
        r.writeln()
        render_typealias_probes(r, hctx.typealias_probes)
```

- [ ] **Step 4: Render class-level probes in pybind11 helper output**

In `src/semiwrap/autowrap/render_pybind11.py`, add this import near existing imports:

```python
from .typealias_probe import render_typealias_probes
```

In `cls_user_using`, after rendering `cls.user_typealias`, add:

```python
    if cls.typealias_probes:
        render_typealias_probes(r, cls.typealias_probes)
```

Leave `cls_auto_using` unchanged for now; probes need to appear before class declarations, and `cls_user_using` is already called before `cls_decl` in `render_wrapped_cpp`.

- [ ] **Step 5: Run `.cpp` render tests and verify they pass**

Run:

```bash
pytest tests/test_typealias_probe.py::test_render_wrapped_cpp_emits_global_typealias_probe_before_initializer tests/test_typealias_probe.py::test_render_wrapped_cpp_emits_class_typealias_probe_inside_initializer -q
```

Expected: PASS, both tests pass.

- [ ] **Step 6: Run all probe tests**

Run:

```bash
pytest tests/test_typealias_probe.py -q
```

Expected: PASS, all tests in `tests/test_typealias_probe.py` pass.

- [ ] **Step 7: Commit `.cpp` rendering**

```bash
git add src/semiwrap/autowrap/render_wrapped.py src/semiwrap/autowrap/render_pybind11.py tests/test_typealias_probe.py
git commit -m "Render typealias probes in wrapper cpp"
```

---

### Task 4: Render probes in generated trampoline headers

**Files:**
- Modify: `src/semiwrap/autowrap/render_cls_trampoline_hpp.py`
- Test: `tests/test_typealias_probe.py`

**Interfaces:**
- Consumes from Task 1:
  - `render_typealias_probes(r: RenderBuffer, probes: Sequence[str], *, indent: str = "") -> None`
- Consumes from Task 2:
  - `ClassContext.typealias_probes`
- Produces generated trampoline `.hpp` output containing class-scope probe aliases before protected constructors and virtual/protected methods.

- [ ] **Step 1: Add failing trampoline render test**

Append to `tests/test_typealias_probe.py`:

```python
from semiwrap.autowrap.render_cls_trampoline_hpp import render_cls_trampoline_hpp


def test_render_trampoline_hpp_emits_class_typealias_probe():
    hctx = parse_fixture_header("using.h", "using.yml")
    cls = next(c for c in hctx.classes if c.cpp_name == "ProtectedUsing")
    out = render_cls_trampoline_hpp(hctx, cls)
    probe = "semiwrap_typealias_probe_CantResolve__add_typealias_to_yaml"
    assert probe in out
    assert out.index(probe) < out.index("PyTrampoline_ProtectedUsing(CantResolve")
```

- [ ] **Step 2: Run trampoline render test and verify it fails**

Run:

```bash
pytest tests/test_typealias_probe.py::test_render_trampoline_hpp_emits_class_typealias_probe -q
```

Expected: FAIL because generated trampoline output does not contain `semiwrap_typealias_probe_`.

- [ ] **Step 3: Render class-level probes in trampoline classes**

In `src/semiwrap/autowrap/render_cls_trampoline_hpp.py`, add this import near existing imports:

```python
from .typealias_probe import render_typealias_probes
```

Inside `_render_cls_trampoline`, in the existing `with r.indent():` block that emits child classes, enums, `cls.user_typealias`, and `cls.auto_typealias`, add this after the `cls.auto_typealias` loop and before the `if cls.constants:` block:

```python
        if cls.typealias_probes:
            render_typealias_probes(r, cls.typealias_probes)
```

- [ ] **Step 4: Run trampoline render test and verify it passes**

Run:

```bash
pytest tests/test_typealias_probe.py::test_render_trampoline_hpp_emits_class_typealias_probe -q
```

Expected: PASS.

- [ ] **Step 5: Run all probe tests**

Run:

```bash
pytest tests/test_typealias_probe.py -q
```

Expected: PASS, all tests in `tests/test_typealias_probe.py` pass.

- [ ] **Step 6: Commit trampoline rendering**

```bash
git add src/semiwrap/autowrap/render_cls_trampoline_hpp.py tests/test_typealias_probe.py
git commit -m "Render typealias probes in trampolines"
```

---

### Task 5: Add generated fixture assertions and run integration tests

**Files:**
- Modify: `tests/test_ft_misc.py`

**Interfaces:**
- Consumes generated files under `tests/cpp/sw-test/build/*/semiwrap/` created by the existing `tests/run_tests.py` install/build flow.
- Produces regression coverage that the real `using.h` fixture emits typealias probes in built generated C++.

- [ ] **Step 1: Add failing fixture-output test**

Append this test under the `# using.h / using2.h` section in `tests/test_ft_misc.py`:

```python
def test_using_generated_typealias_probes_present():
    from pathlib import Path

    root = Path(__file__).parent / "cpp" / "sw-test" / "build"
    using_cpp_files = sorted(root.glob("*/semiwrap/using.cpp"))
    assert using_cpp_files, "sw-test build did not generate semiwrap/using.cpp"
    using_cpp = using_cpp_files[-1].read_text()

    assert "semiwrap_typealias_probe_AlsoCantResolve__add_typealias_to_yaml" in using_cpp
    assert "using semiwrap_typealias_probe_AlsoCantResolve__add_typealias_to_yaml" in using_cpp
    assert "= AlsoCantResolve;" in using_cpp
    assert "semiwrap_typealias_probe_CantResolve__add_typealias_to_yaml" in using_cpp
    assert "= CantResolve;" in using_cpp

    trampoline_files = sorted(
        root.glob("*/semiwrap/trampolines/cr__inner__ProtectedUsing.hpp")
    )
    assert trampoline_files, (
        "sw-test build did not generate trampoline for cr::inner::ProtectedUsing"
    )
    trampoline_hpp = trampoline_files[-1].read_text()
    assert "semiwrap_typealias_probe_CantResolve__add_typealias_to_yaml" in trampoline_hpp
    assert "add a typealias entry for `CantResolve`" in trampoline_hpp
```

- [ ] **Step 2: Run the fixture test and verify it passes after a rebuild**

Run:

```bash
python tests/run_tests.py tests/test_ft_misc.py::test_using_generated_typealias_probes_present -q
```

Expected: PASS. The command first rebuilds the C++ fixtures, then pytest finds the generated `using.cpp` and trampoline header with probe aliases.

If this fails because the trampoline file name differs, run:

```bash
find tests/cpp/sw-test/build -path '*/semiwrap/trampolines/*ProtectedUsing*.hpp' -print
```

Expected: one printed path. Replace `cr__inner__ProtectedUsing.hpp` in the test with the actual generated basename and rerun the `python tests/run_tests.py ...` command.

- [ ] **Step 3: Run focused Python/unit tests**

Run:

```bash
pytest tests/test_typealias_probe.py -q
```

Expected: PASS.

- [ ] **Step 4: Run focused existing runtime test**

Run:

```bash
pytest tests/test_ft_misc.py::test_using_fwddecl tests/test_ft_misc.py::test_using_generated_typealias_probes_present -q
```

Expected: PASS when the C++ fixture has already been built by Step 2.

- [ ] **Step 5: Commit fixture assertions**

```bash
git add tests/test_ft_misc.py
git commit -m "Test generated typealias probes in fixture build"
```

---

### Task 6: Full verification and cleanup

**Files:**
- No new files.
- May modify any implementation/test file from earlier tasks only if verification exposes a concrete defect.

**Interfaces:**
- Consumes all prior tasks.
- Produces a verified branch with passing focused tests and clean git status.

- [ ] **Step 1: Run probe unit tests**

Run:

```bash
pytest tests/test_typealias_probe.py -q
```

Expected: PASS.

- [ ] **Step 2: Run C++ fixture rebuild and focused tests**

Run:

```bash
python tests/run_tests.py tests/test_ft_misc.py::test_using_fwddecl tests/test_ft_misc.py::test_using_generated_typealias_probes_present -q
```

Expected: PASS.

- [ ] **Step 3: Run the full test suite if time permits**

Run:

```bash
python tests/run_tests.py
```

Expected: PASS. If this command is too slow for the environment, record the timeout/runtime limitation and keep the focused passing commands from Steps 1-2 as verification evidence.

- [ ] **Step 4: Inspect generated diagnostic output manually**

Run:

```bash
python - <<'PY'
from pathlib import Path
root = Path('tests/cpp/sw-test/build')
for p in sorted(root.glob('*/semiwrap/using.cpp'))[-1:]:
    text = p.read_text()
    for line in text.splitlines():
        if 'semiwrap_typealias_probe_' in line or 'semiwrap diagnostic' in line:
            print(line)
PY
```

Expected output includes lines similar to:

```text
// semiwrap diagnostic: if this line fails because `AlsoCantResolve` is unknown,
using semiwrap_typealias_probe_AlsoCantResolve__add_typealias_to_yaml [[maybe_unused]] = AlsoCantResolve;
// semiwrap diagnostic: if this line fails because `CantResolve` is unknown,
using semiwrap_typealias_probe_CantResolve__add_typealias_to_yaml [[maybe_unused]] = CantResolve;
```

- [ ] **Step 5: Check git status**

Run:

```bash
git status --short
```

Expected: no uncommitted tracked implementation/test changes. Ignored build artifacts under `tests/cpp/*/build` are acceptable and should not be committed.

- [ ] **Step 6: Commit any verification fixes**

Only if Step 1, 2, 3, or 4 required code/test changes, commit them:

```bash
git add src/semiwrap/autowrap tests/test_typealias_probe.py tests/test_ft_misc.py
git commit -m "Fix typealias probe verification issues"
```

Expected: either a new commit is created for concrete fixes, or there is nothing to commit.
