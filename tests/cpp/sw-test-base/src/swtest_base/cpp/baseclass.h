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
