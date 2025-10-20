
#pragma once

struct TClassWithFn
{
    template <typename T>
    static T getT(T t)
    {
        return t;
    }
};

template <int I>
struct TTClassWithFn
{
    template <typename T>
    static T getT(T t)
    {
        return t + I;
    }
};

auto abbrv_fn_tmpl(auto t) {
    return t + 2;
}

template <typename T>
T tmpl_fn(T t) {
    return t + 1;
}
