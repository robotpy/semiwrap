
#pragma once

#include <nanobind/nanobind.h>

namespace nb = nanobind;

// Py_IsFinalizing is public API in 3.13
#if PY_VERSION_HEX < 0x030D0000
#define Py_IsFinalizing _Py_IsFinalizing
#endif

namespace semiwrap {

/*
    This object holds a python object, and can be stored in C++ containers that
    aren't pybind11 aware.

    It is very inefficient -- it will acquire and release the GIL each time
    a move/copy operation occurs! You should only use this object type as a
    last resort.

    Assigning, moves, copies, and destruction acquire the GIL; only converting
    this back into a python object requires holding the GIL.
*/
template <typename T>
class gilsafe_t final {
    nb::object o;

public:

    //
    // These operations require the caller to hold the GIL
    //

    // copy conversion
    operator nb::object() const & {
        return o;
    }

    // move conversion
    operator nb::object() const && {
        return std::move(o);
    }

    //
    // These operations do not require the caller to hold the GIL
    //

    gilsafe_t() = default;

    ~gilsafe_t() {
        if (o) {
            // If the interpreter is alive, acquire the GIL, otherwise just leak
            // the object to avoid a crash
            if (!Py_IsFinalizing()) {
                nb::gil_scoped_acquire lock;
                o.dec_ref();
            }

            o.release();
        }
    }

    // Copy constructor; always increases the reference count
    gilsafe_t(const gilsafe_t &other) {
        nb::gil_scoped_acquire lock;
        o = other.o;
    }

    // Copy constructor; always increases the reference count
    gilsafe_t(const nb::object &other) {
        nb::gil_scoped_acquire lock;
        o = other;
    }

    gilsafe_t(const nb::handle &other) {
        nb::gil_scoped_acquire lock;
        o = nb::borrow<nb::object>(other);
    }

    // Move constructor; steals object from ``other`` and preserves its reference count
    gilsafe_t(gilsafe_t &&other) noexcept : o(std::move(other.o)) {}

    // Move constructor; steals object from ``other`` and preserves its reference count
    gilsafe_t(nb::object &&other)  noexcept : o(std::move(other)) {}

    // copy assignment
    gilsafe_t &operator=(const gilsafe_t& other) {
        if (!o.is(other.o)) {
            nb::gil_scoped_acquire lock;
            o = other.o;
        }
        return *this;
    }

    // move assignment
    gilsafe_t &operator=(gilsafe_t&& other) noexcept {
        if (this != &other) {
            nb::gil_scoped_acquire lock;
            o = std::move(other.o);
        }
        return *this;
    }

    explicit operator bool() const {
        return (bool)o;
    }

    nb::handle borrow() const {
        return o.inc_ref();
    }
};

// convenience alias
using gilsafe_object = gilsafe_t<nb::object>;

} // namespace semiwrap



NAMESPACE_BEGIN(NB_NAMESPACE)
NAMESPACE_BEGIN(detail)

template <typename T>
struct type_caster<semiwrap::gilsafe_t<T>> {
    NB_TYPE_CASTER(semiwrap::gilsafe_t<T>, make_caster<T>::Name);

    bool from_python(handle src, uint8_t, cleanup_list *) noexcept {
        value = src;
        return true;
    }

    static handle from_cpp(const semiwrap::gilsafe_t<T> &src,
                           rv_policy,
                           cleanup_list *) noexcept {
        return src.borrow();
    }
};

NAMESPACE_END(detail)
NAMESPACE_END(NB_NAMESPACE)
