#pragma once

template <typename T>
struct Outer
{
    struct Inner
    {
        T t;
    };
};

struct LocalOuter
{
    template <typename T>
    struct Inner
    {
        explicit Inner(T value) : value(value) {}

        T get() const { return value; }

        T value;
    };
};

template <typename T>
struct TemplatedOuter
{
    template <typename U>
    struct Inner
    {
        Inner(T outer, U inner) : outer(outer), inner(inner) {}

        T getOuter() const { return outer; }
        U getInner() const { return inner; }

        T outer;
        U inner;
    };
};
