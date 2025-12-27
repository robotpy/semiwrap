#pragma once

//
// From pybind11 documentation
//

#include <pybind11/pybind11.h>

namespace pybind11::detail {

template <int Offset>
struct type_caster<int_ns::IntWithOffset<Offset>> {
  PYBIND11_TYPE_CASTER(int_ns::IntWithOffset<Offset>, const_name("swtest_base.offset") + const_name<Offset>());

  bool load(handle src, bool) {
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

  static handle cast(int_ns::IntWithOffset<Offset> src, return_value_policy /* policy */, handle /* parent */) {
    return PyLong_FromLong(src.Get());
  }
};

}  // namespace pybind11::detail