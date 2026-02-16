
#pragma once

#include <gilsafe_object.h>

class GilsafeContainer {
    semiwrap::gilsafe_object m_o;
public:
    void assign(semiwrap::gilsafe_object o) {
        m_o = o;
    }

    static void check() {
        auto c = std::make_unique<GilsafeContainer>();

        nb::gil_scoped_acquire a;

        nb::object v = nb::none();

        {
            nb::gil_scoped_release r;
            c->assign(v);
            c.reset();
        }
    }

};
