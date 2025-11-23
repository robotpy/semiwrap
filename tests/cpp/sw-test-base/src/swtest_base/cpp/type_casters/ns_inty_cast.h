#pragma once

//
// From pybind11 documentation, converted to nanobind
//

#include <nanobind/nanobind.h>

#include "../ns_inty.h"

NAMESPACE_BEGIN(NB_NAMESPACE)
NAMESPACE_BEGIN(detail)

template <> struct type_caster<ns::inty2> {
public:
    /**
        * This macro establishes the name 'inty' in
        * function signatures and declares a local variable
        * 'value' of type inty
        */
    NB_TYPE_CASTER(ns::inty2, const_name("swtest_base.inty"));

    /**
        * Conversion part 1 (Python->C++): convert a PyObject into a inty
        * instance or return false upon failure. The second argument
        * indicates whether implicit conversions should be applied.
        */
    bool from_python(handle src, uint8_t, cleanup_list *) noexcept {
        /* Extract PyObject from handle */
        PyObject *source = src.ptr();
        /* Try converting into a Python integer value */
        PyObject *tmp = PyNumber_Long(source);
        if (!tmp)
            return false;
        /* Now try to convert into a C++ int */
        value.long_value = PyLong_AsLong(tmp);
        Py_DECREF(tmp);
        /* Ensure return code was OK (to avoid out-of-range errors etc) */
        return !(value.long_value == -1 && !PyErr_Occurred());
    }

    /**
        * Conversion part 2 (C++ -> Python): convert an inty instance into
        * a Python object. The second and third arguments are used to
        * indicate the return value policy and parent object (for
        * ``return_value_policy::reference_internal``) and are generally
        * ignored by implicit casters.
        */
    static handle from_cpp(const ns::inty2 &value, rv_policy,
                           cleanup_list *) noexcept {
        return PyLong_FromLong(value.long_value);
    }
};

NAMESPACE_END(detail)
NAMESPACE_END(NB_NAMESPACE)
