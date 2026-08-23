#pragma once

#include <string>

inline int defaultArgsKwOnly(int required, int optional = 10)
{
    return required + optional;
}

inline int defaultArgsPositionalOptOut(int required, int optional = 20)
{
    return required + optional;
}

inline int noDefaultThenKwOnly(int required, int positional = 20, int keyword = 30)
{
    return required + positional + keyword;
}

inline int overloadKwOnlyOptOut(int value, int increment = 1)
{
    return value + increment;
}

inline std::string overloadKwOnlyOptOut(const char *value, const char *suffix = "!")
{
    return std::string(value) + suffix;
}

inline int overloadKwOnlyOptIn(int value, int increment = 1)
{
    return value + increment;
}

inline std::string overloadKwOnlyOptIn(const char *value, const char *suffix = "!")
{
    return std::string(value) + suffix;
}

struct DefaultArgsMethod
{
    int calculate(int required, int optional = 40)
    {
        return required + optional;
    }

    int calculatePositional(int required, int optional = 50)
    {
        return required + optional;
    }
};
