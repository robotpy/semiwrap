#pragma once

//
// From pybind11 documentation, converted to nanobind
//

#include <nanobind/nanobind.h>

NAMESPACE_BEGIN(NB_NAMESPACE)
NAMESPACE_BEGIN(detail)

template <int Offset>
struct type_caster<int_ns::IntWithOffset<Offset>> {
  
  NB_TYPE_CASTER(int_ns::IntWithOffset<Offset>, const_name("swtest_base.offset") + const_name<Offset>());

  bool from_python(handle src, uint8_t, cleanup_list *) noexcept {
    /* Extract PyObject from handle */
    PyObject *source = src.ptr();
    /* Try converting into a Python integer value */
    PyObject *tmp = PyNumber_Long(source);
    if (!tmp)
      return false;
    /* Now try to convert into a C++ int */
    value.Set(PyLong_AsLong(tmp));
    Py_DECREF(tmp);
    /* Ensure return code was OK (to avoid out-of-range errors etc) */
    return !(value.Get() == -1 && !PyErr_Occurred());
  }

  static handle from_cpp(const int_ns::IntWithOffset<Offset> &src, rv_policy, cleanup_list *) {
    return PyLong_FromLong(src.Get());
  }
};

NAMESPACE_END(detail)
NAMESPACE_END(NB_NAMESPACE)
