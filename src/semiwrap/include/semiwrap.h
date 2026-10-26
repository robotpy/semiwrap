#pragma once

// Base definitions used by all semiwrap projects

#include <pybind11/pybind11.h>

namespace py = pybind11;

// Use this to release the gil
typedef py::call_guard<py::gil_scoped_release> release_gil;

//
// Deprecated APIs
//

// Suppress deprecation warnings when binding deprecated C++ APIs
#if defined(__clang__)
#define SEMIWRAP_IGNORE_DEPRECATED_PUSH \
    _Pragma("clang diagnostic push") \
    _Pragma("clang diagnostic ignored \"-Wdeprecated-declarations\"")
#define SEMIWRAP_IGNORE_DEPRECATED_POP _Pragma("clang diagnostic pop")
#elif defined(__GNUC__)
#define SEMIWRAP_IGNORE_DEPRECATED_PUSH \
    _Pragma("GCC diagnostic push") \
    _Pragma("GCC diagnostic ignored \"-Wdeprecated-declarations\"")
#define SEMIWRAP_IGNORE_DEPRECATED_POP _Pragma("GCC diagnostic pop")
#elif defined(_MSC_VER)
#define SEMIWRAP_IGNORE_DEPRECATED_PUSH \
    __pragma(warning(push)) \
    __pragma(warning(disable : 4996))
#define SEMIWRAP_IGNORE_DEPRECATED_POP __pragma(warning(pop))
#else
#define SEMIWRAP_IGNORE_DEPRECATED_PUSH
#define SEMIWRAP_IGNORE_DEPRECATED_POP
#endif

namespace semiwrap {

// pybind11 function attribute that emits a python DeprecationWarning when
// the bound function is called. Msg is a type with a static value() function
// that returns the message.
template <typename Msg>
struct deprecated {};

// The message is carried by a unique local type so that this works without
// C++20 class-type non-type template parameters
#define SEMIWRAP_DEPRECATED(msg) \
    [] { \
        struct semiwrap_deprecated_msg { \
            static const char *value() { return msg; } \
        }; \
        return semiwrap::deprecated<semiwrap_deprecated_msg>(); \
    }()

} // namespace semiwrap

PYBIND11_NAMESPACE_BEGIN(PYBIND11_NAMESPACE)
PYBIND11_NAMESPACE_BEGIN(detail)

template <typename Msg>
struct process_attribute<semiwrap::deprecated<Msg>>
    : process_attribute_default<semiwrap::deprecated<Msg>> {
    // called with the GIL held after arguments are converted, before any
    // call guard (such as release_gil) is applied
    static void precall(function_call &) {
        if (PyErr_WarnEx(PyExc_DeprecationWarning, Msg::value(), 1) != 0) {
            throw error_already_set();
        }
    }
};

PYBIND11_NAMESPACE_END(detail)
PYBIND11_NAMESPACE_END(PYBIND11_NAMESPACE)

// empty trampoline configuration base
namespace swgen {
struct EmptyTrampolineCfg {};
};

#define SEMIWRAP_BAD_TRAMPOLINE \
    "has an abstract trampoline -- and they must never be abstract! One of " \
    "the generated override methods doesn't match the original class or its " \
    "bases, or is missing. You will need to provide method and/or param " \
    "overrides for that method. It is likely the following compiler error " \
    "messages will tell you which one it is."


// only for use by SEMIWRAP_OVERRIDE_PURE_POST_IMPL
template <class T> py::handle __get_handle(const T *this_ptr) {
    auto this_type = py::detail::get_type_info(typeid(T));
    if (!this_type) return py::handle();
    return py::detail::get_object_handle(this_ptr, this_type);
}

#define SEMIWRAP_OVERRIDE_CUSTOM_IMPL(ret_type, cname, name, ...)                         \
    do {                                                                                  \
        py::gil_scoped_acquire gil;                                                       \
        py::function override = py::get_override(static_cast<const cname *>(this), name); \
        if (override)                                                                     \
        {                                                                                 \
            return custom_fn(override);                                                   \
        }                                                                                 \
    } while (false)

#define SEMIWRAP_OVERRIDE_PURE_POST_IMPL(pyname, cname, name)                                                                          \
    std::string __msg("<unknown> does not override required function \"" PYBIND11_STRINGIFY(pyname) "::" name "\"");                   \
    try                                                                                                                                \
    {                                                                                                                                  \
        py::gil_scoped_acquire gil;                                                                                                    \
        auto self = __get_handle(static_cast<const cname *>(this));                                                                    \
        if (self)                                                                                                                      \
        {                                                                                                                              \
            __msg = std::string(py::repr(self)) + " does not override required function \"" PYBIND11_STRINGIFY(pyname) "::" name "\""; \
        }                                                                                                                              \
    }                                                                                                                                  \
    catch (std::exception &)                                                                                                           \
    {                                                                                                                                  \
    }                                                                                                                                  \
    {                                                                                                                                  \
        py::gil_scoped_acquire gil;                                                                                                    \
        py::pybind11_fail(__msg);                                                                                                       \
    }

#define SEMIWRAP_OVERRIDE_PURE_CUSTOM_NAME(pyname, ret_type, cname, name, fn, ...)                      \
    {                                                                                                   \
        SEMIWRAP_OVERRIDE_CUSTOM_IMPL(PYBIND11_TYPE(ret_type), PYBIND11_TYPE(cname), name, __VA_ARGS__);\
        SEMIWRAP_OVERRIDE_PURE_POST_IMPL(pyname, PYBIND11_TYPE(cname), name);                           \
    }

#define SEMIWRAP_OVERRIDE_PURE_NAME(pyname, ret_type, cname, name, fn, ...)                      \
    {                                                                                            \
        PYBIND11_OVERRIDE_IMPL(PYBIND11_TYPE(ret_type), PYBIND11_TYPE(cname), name, __VA_ARGS__);\
        SEMIWRAP_OVERRIDE_PURE_POST_IMPL(pyname, PYBIND11_TYPE(cname), name);                    \
    }

#define SEMIWRAP_OVERRIDE_CUSTOM_NAME(ret_type, cname, name, fn, ...)                               \
    SEMIWRAP_OVERRIDE_CUSTOM_IMPL(PYBIND11_TYPE(ret_type), PYBIND11_TYPE(cname), name, __VA_ARGS__);\
    return cname::fn(__VA_ARGS__)

//
// backwards compat
//

#define SEMIWRAP_OVERLOAD_PURE_CUSTOM_NAME(pyname, ret_type, cname, name, fn, ...) \
    SEMIWRAP_OVERRIDE_PURE_CUSTOM_NAME(pyname, PYBIND11_TYPE(ret_type), PYBIND11_TYPE(cname), name, fn, __VA_ARGS__)
#define SEMIWRAP_OVERLOAD_CUSTOM_NAME(ret_type, cname, name, fn, ...) \
    SEMIWRAP_OVERRIDE_CUSTOM_NAME(PYBIND11_TYPE(ret_type), PYBIND11_TYPE(cname), name, fn, __VA_ARGS__)
#define SEMIWRAP_OVERLOAD_PURE_NAME(pyname, ret_type, cname, name, fn, ...) \
    SEMIWRAP_OVERRIDE_PURE_NAME(pyname, PYBIND11_TYPE(ret_type), PYBIND11_TYPE(cname), name, fn, __VA_ARGS__)
