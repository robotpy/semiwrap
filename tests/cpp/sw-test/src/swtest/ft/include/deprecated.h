#pragma once

[[deprecated("use fnNotDeprecated instead")]]
inline int fnDeprecated() { return 1; }

inline int fnNotDeprecated() { return 2; }

// message split across adjacent string literals
[[deprecated("multiple " "literals")]]
inline int fnDeprecatedMultiLiteral() { return 3; }

// no message
[[deprecated]]
inline int fnDeprecatedNoMessage() { return 4; }

struct DeprecatedMembers {
    DeprecatedMembers() = default;

    [[deprecated("deprecated constructor")]]
    DeprecatedMembers(int x) : notDeprecatedField(x) {}

    [[deprecated("deprecated method")]]
    int deprecatedMethod() { return 5; }

    // released gil
    [[deprecated("deprecated static method")]]
    static int deprecatedStaticMethod() { return 6; }

    // only one overload is deprecated
    int overloaded(int x) { return x; }

    [[deprecated("deprecated overload")]]
    int overloaded(double x) { return (int)x + 1; }

    [[deprecated("deprecated virtual")]]
    virtual int deprecatedVirtual() { return 7; }

    int callDeprecatedVirtual() {
        // calling this from C++ is still deprecated
#if defined(__clang__) || defined(__GNUC__)
#pragma GCC diagnostic push
#pragma GCC diagnostic ignored "-Wdeprecated-declarations"
#elif defined(_MSC_VER)
#pragma warning(push)
#pragma warning(disable : 4996)
#endif
        return deprecatedVirtual();
#if defined(__clang__) || defined(__GNUC__)
#pragma GCC diagnostic pop
#elif defined(_MSC_VER)
#pragma warning(pop)
#endif
    }

    virtual ~DeprecatedMembers() = default;

    int notDeprecatedField = 0;
};

// no default member initializer, otherwise the implicit constructor would
// warn when compiling this header
struct DeprecatedField {
    [[deprecated("deprecated field")]]
    int deprecatedField;
};
