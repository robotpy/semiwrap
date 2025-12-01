#pragma once

// Base definitions used by all semiwrap projects

#include <nanobind/nanobind.h>

namespace nb = nanobind;

// Use this to release the gil
typedef nb::call_guard<nb::gil_scoped_release> release_gil;

namespace swgen {

// empty trampoline configuration base
struct EmptyTrampolineCfg {};

};

#define SEMIWRAP_BAD_TRAMPOLINE \
    "has an abstract trampoline -- and they must never be abstract! One of " \
    "the generated override methods doesn't match the original class or its " \
    "bases, or is missing. You will need to provide method and/or param " \
    "overrides for that method. It is likely the following compiler error " \
    "messages will tell you which one it is."

//
// Semiwrap provides versions of NB_OVERRIDE_* macros to work around limitations
// in nanobind's macros
//

#define SEMIWRAP_OVERRIDE_XFORM(name, func, ...)                                \
    nanobind::detail::ticket nb_ticket(nb_trampoline, name, false);             \
    if (nb_ticket.key.is_valid()) {                                             \
        return custom_fn(nb_trampoline.base().attr(nb_ticket.key));             \
    }

#define SEMIWRAP_OVERRIDE_XFORM_PURE(name, func, ...)                           \
    nanobind::detail::ticket nb_ticket(nb_trampoline, name, true);              \
    return custom_fn(nb_trampoline.base().attr(nb_ticket.key))


#define SEMIWRAP_OVERRIDE_PURE_NAME(name, func, ...)                           \
    nanobind::detail::ticket nb_ticket(nb_trampoline, name, true);             \
    return nanobind::cast<nb_ret_type>(                                        \
        nb_trampoline.base().attr(nb_ticket.key)(__VA_ARGS__))

#define SEMIWRAP_OVERRIDE_NAME(name, func, ...) NB_OVERRIDE_NAME(name, func, __VA_ARGS__)
