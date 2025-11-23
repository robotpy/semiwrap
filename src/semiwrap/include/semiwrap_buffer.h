#pragma once

#include <nanobind/nanobind.h>

namespace nb = nanobind;

// Nanobind doesn't have an equivalent of py::buffer, so we make one here
namespace semiwrap {

struct buffer_info {
    Py_ssize_t size = 0;
    Py_buffer *view = nullptr;

    buffer_info() = default;
    buffer_info(Py_buffer *view) : size(1) {
        this->view = view;
        for (size_t i = 0; i < (size_t) view->ndim; ++i) {
            size *= view->shape[i];
        }
    }

    buffer_info(const buffer_info&) = delete;
    buffer_info& operator=(const buffer_info&) = delete;

    buffer_info(buffer_info &&other) noexcept { (*this) = std::move(other); }
    buffer_info &operator=(buffer_info &&rhs) noexcept {
        size = rhs.size;
        std::swap(view, rhs.view);
        return *this;
    }

    ~buffer_info() {
        if (view) {
            PyBuffer_Release(view);
        }
    }  
};

class buffer : public nb::object {
    NB_OBJECT_DEFAULT(buffer, object, "buffer", PyObject_CheckBuffer)

    buffer_info request(bool writable = false) const {
        int flags = PyBUF_STRIDES | PyBUF_FORMAT;
        if (writable) {
            flags |= PyBUF_WRITABLE;
        }
        auto *view = new Py_buffer();
        if (PyObject_GetBuffer(m_ptr, view, flags) != 0) {
            delete view;
            throw nb::python_error();
        }
        return buffer_info(view);
    }
};

}; // namespace semiwrap
