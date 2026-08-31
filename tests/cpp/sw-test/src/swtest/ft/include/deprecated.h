#pragma once

[[deprecated]] inline int deprecated_without_message() {
    return 1;
}

[[deprecated("Use " "current_free_function().")]] inline int deprecated_free_function() {
    return 2;
}

/**
 * Legacy documented function.
 *
 * .. warning::<br>   Deprecated: Use current_documented_function().
 */
[[deprecated("Use current_documented_function().")]] inline int deprecated_documented_function() {
    return 3;
}

class DeprecatedMembers {
public:
    [[deprecated("Use DeprecatedMembers::create().")]] DeprecatedMembers() = default;

    [[deprecated("Use current_method().")]] int deprecated_method() const {
        return 4;
    }

    [[deprecated("Use current_static_method().")]] static int deprecated_static_method() {
        return 5;
    }

    [[deprecated("Use operator!=().")]] bool operator==(
        const DeprecatedMembers &other) const {
        return this == &other;
    }

    /** Legacy member field. */
    [[deprecated("Use current_field.")]] int deprecated_field;

    /** Legacy static field. */
    [[deprecated("Use current_static_field.")]] static constexpr int deprecated_static_field = 7;
};

/** Legacy class. */
class [[deprecated("Use CurrentClass.")]] DeprecatedClass {
public:
    DeprecatedClass() = default;

    int value() const {
        return 8;
    }
};

enum class [[deprecated("Use CurrentEnum.")]] DeprecatedEnum {
    Value = 9,
};

enum class MixedDeprecatedEnum {
    DeprecatedValue [[deprecated("Use MixedDeprecatedEnum::CurrentValue.")]] = 10,
    CurrentValue = 11,
};

class DeprecatedVirtual {
public:
    virtual ~DeprecatedVirtual() = default;

    [[deprecated("Use current_virtual().")]] virtual int deprecated_virtual() {
        return 12;
    }

protected:
    [[deprecated("Use current_protected_method().")]] int deprecated_protected_method() {
        return 13;
    }

    /** Legacy protected property. */
    [[deprecated("Use current_protected_property.")]] int deprecated_protected_property;
};

/** Legacy class template. */
template <typename T>
class [[deprecated("Use CurrentTemplate.")]] DeprecatedTemplate {
public:
    DeprecatedTemplate() = default;

    T get() const {
        return T{15};
    }
};
