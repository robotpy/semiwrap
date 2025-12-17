
#include "static_only.h"

struct StaticOnly2::SO2Impl {
    int n = 0;
};

StaticOnly2& StaticOnly2::getInstance()
{
    static StaticOnly2 inst;
    return inst;
}

StaticOnly2::StaticOnly2() {
    m_impl = std::make_unique<StaticOnly2::SO2Impl>();
}

void StaticOnly2::setNumber(int n)
{
    m_impl->n = n;
}

int StaticOnly2::getNumber()
{
    return m_impl->n;
}
