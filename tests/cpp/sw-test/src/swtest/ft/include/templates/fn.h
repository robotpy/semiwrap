
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

template <int X>
int tmpl_fn_add(int x) {
    return x + X;
}

template <typename T>
T tmpl_fn(T t) {
    return t + 1;
}

template <typename T>
T overloadedTFn(T v) {
    return v;
}

template <typename T>
T overloadedTFn(T v, T v2) {
    return v + v2;
}

auto overloadedTFn(auto v1, auto v2, auto v3) {
    return v1 + v2 + v3;
}
