# Compile-time diagnostics for missing `typealias` entries

## Problem

When semiwrap parses a header that uses locally visible aliases or using-declarations, it may emit generated C++ that refers to a short type name such as `CantResolve`. If that name is not visible in the generated binding scope, the user currently sees an opaque C++/pybind11 compile error. The error can be much worse when generated trampolines and base-class trampoline composition are involved.

Semiwrap cannot definitively know during YAML/header processing whether a short C++ name will resolve in every generated C++ context. The diagnostic should therefore remain a compile-time diagnostic in generated C++.

## Design

Generate fail-fast C++ alias probes for type names that are likely to need a YAML `typealias` entry. A probe is a `using` declaration placed before the generated binding or trampoline code uses the type:

```cpp
// semiwrap diagnostic: if this line fails because `CantResolve` is unknown,
// add a typealias entry for it to the semiwrap yaml file.
using semiwrap_typealias_probe_CantResolve = CantResolve;
```

If `CantResolve` is not visible, compilation fails at this probe instead of deep inside pybind11 or trampoline templates. The compiler may not show a custom `static_assert` message, but the failing generated alias name and nearby comment identify the likely fix.

## Scope placement

Probes must be emitted in the same generated scope where the unresolved-prone type will later be used.

- For normal binding code, emit probes in the generated `.cpp` near existing user/auto typealiases and before `py::class_`, method, constructor, or function binding expressions that use the type.
- For classes with trampolines, emit class-scope probes in the generated trampoline `.hpp` before constructors, methods, and inherited trampoline composition use the type.
- Keep the generated probe names unique and deterministic so multiple probes cannot collide.

## Candidate types

Start with type spellings that semiwrap already emits in generated signatures, such as function return types and parameter types. Derive the probe target from the parsed type's base spelling, not from the full decorated spelling, so `const CantResolve&` produces a probe for `CantResolve`.

Only add probes for names that are plausible unresolved aliases:

- include unqualified or partially qualified names that appear in generated signatures;
- skip C++ built-in/fundamental types;
- skip names that are already fully qualified with a leading `::`;
- skip obvious standard-library names and other names semiwrap intentionally qualifies itself.

This keeps noise low while targeting cases like the `using.h` testcase.

The probe list is best-effort. It does not need to prove that a name is unresolved; it only needs to move failures for suspicious names to an earlier, clearer location. If a candidate type is already resolved, the probe compiles away as a harmless alias.

## Rejected alternatives

- Generation-time error or warning: semiwrap cannot reliably know whether C++ name lookup will succeed in generated contexts.
- `static_assert`-based type existence checks: C++ name lookup for a missing non-dependent type fails before `static_assert` or SFINAE can provide a custom diagnostic.
- Placeholder declarations for missing names: declaring dummy types changes name lookup, can shadow real types, and may make invalid code fail in misleading ways.
- Unconditional `#warning`/`#pragma message`: explicit but noisy and less portable. This can be considered later as an opt-in debug mode if needed.

## Testing

Add or adjust tests around the existing `using.h` testcase to verify the generated C++ contains typealias probes for short alias-like type names. A compile-failure fixture can then remove the YAML `typealias` and assert the compiler output points at the semiwrap probe name/comment area rather than pybind11/trampoline internals, if the test harness supports expected build failures.
