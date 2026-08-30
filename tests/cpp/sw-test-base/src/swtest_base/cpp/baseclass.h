#pragma  once

#include <string>

// tests trampoline across packages
class abaseclass {
public:
    virtual ~abaseclass() = default;

    inline virtual std::string fn() {
        return "abaseclass";
    }

};

template <typename T>
class RemoteTemplate {
public:
    RemoteTemplate(T value) : value(value) {}

    T get() const {
        return value;
    }

private:
    T value;
};

namespace provider_nested {
struct Outer {
    template <typename T>
    struct Inner {
        explicit Inner(T value) : value(value) {}

        T get() const {
            return value;
        }

    private:
        T value;
    };
};
} // namespace provider_nested

#ifdef PYBIND11_VERSION_MAJOR
// User declarations must not collide with semiwrap's generated header types.
template <typename CfgBase>
struct PyTrampolineCfg_abaseclass {};

template <typename PyTrampolineBase, typename PyTrampolineCfg>
struct PyTrampoline_abaseclass {};

namespace swgen {
template <typename T>
struct bind___RemoteTemplate {};
} // namespace swgen
#endif
