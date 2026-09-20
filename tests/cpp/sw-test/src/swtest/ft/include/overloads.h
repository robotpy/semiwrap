#pragma once

// Template bindings include this header in multiple translation units.
inline int bindingOrder(int value) { return 1; }
inline int bindingOrder(long value) { return 2; }

inline int bindingOrderUnchanged(int value) { return 1; }
inline int bindingOrderUnchanged(long value) { return 2; }

inline int bindingOrderLater(int value) { return 1; }
inline int bindingOrderLater(long value) { return 2; }

inline int bindingOrderTied(int value, int skip = 0) { return 1; }
inline int bindingOrderTied(long value) { return 2; }
inline int bindingOrderTied(long long value, int skip = 0) { return 3; }

inline int bindingOrderInherited(int value, int subset = 0, int inherited = 0) { return 1; }
inline int bindingOrderInherited(long value, int subset = 0, int inherited = 0) { return 2; }
inline int bindingOrderInherited(long long value, int subset = 0) { return 3; }
inline int bindingOrderInherited(short value) { return 4; }

struct BindingOrder {
    BindingOrder(int value) : selected(1) {}
    BindingOrder(long value) : selected(2) {}
    virtual ~BindingOrder() = default;

    int choose(int value) { return 1; }
    int choose(long value) { return 2; }
    int unchanged(int value) { return 1; }
    int unchanged(long value) { return 2; }
    static int chooseStatic(int value) { return 1; }
    static int chooseStatic(long value) { return 2; }

    int later(int value) { return 1; }
    int later(long value) { return 2; }

    int tied(int value, int skip = 0) { return 1; }
    int tied(long value) { return 2; }
    int tied(long long value, int skip = 0) { return 3; }

    int inherited(int value, int subset = 0, int inherited = 0) { return 1; }
    int inherited(long value, int subset = 0, int inherited = 0) { return 2; }
    int inherited(long long value, int subset = 0) { return 3; }
    int inherited(short value) { return 4; }

    int selected;

protected:
    int chooseProtected(int value) { return 1; }
    int chooseProtected(long value) { return 2; }

    // Declared before public overloads to test the existing public-first order.
    int mixedUnchanged(long value) { return 2; }
    int mixedPrioritized(long value) { return 2; }

public:
    int mixedUnchanged(int value) { return 1; }
    int mixedPrioritized(int value) { return 1; }
};

template <typename T>
struct BindingOrderTemplate {
    int choose(T value) { return 1; }
    int choose(long value) { return 2; }
};

inline int fnOverload(int i, int j)
{
    return j;
}

inline int fnOverload(int i)
{
    return i;
}

struct OverloadedObject
{
    using z = int;

    int overloaded(int i)
    {
        return 0x1;
    }
    int overloaded(const char *i)
    {
        return 0x2;
    }
    // Hack: this tricks CppHeaderParser..
    const z& overloaded(int i, int j)
    {
        o = i + j;
        return o;
    }

    // checking that param override works
    int overloaded(int a, int b, int c) {
        return a + b + c;
    }

    // This shows rtnType is inconsistent in CppHeaderParser
    const OverloadedObject& overloaded() {
        return *this;
    }

    constexpr int overloaded_constexpr(int a, int b) {
        return a + b;
    }

    constexpr int overloaded_constexpr(int a, int b, int c) {
        return a + b + c;
    }

    static int overloaded_static(int i)
    {
        return 0x3;
    }
    static int overloaded_static(const char *i)
    {
        return 0x4;
    }

    void overloaded_private(int a) {}

private:

    // this causes errors if we don't account for it
    void overloaded_private(int a, int b) {}

    int o;
};