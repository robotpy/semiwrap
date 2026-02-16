#pragma once

#include <memory>

class StaticOnly
{
private:
    ~StaticOnly();

public:
    static int callme()
    {
        return 0x56;
    }
};

// this will only compile if never_destruct: true is set in the YML
class StaticOnly2 {
  public:
    StaticOnly2(const StaticOnly2&) = delete;
    StaticOnly2& operator=(const StaticOnly2&) = delete;

    static StaticOnly2& getInstance();

    void setNumber(int n);
    int getNumber();

  private:
    StaticOnly2();

    struct SO2Impl;
    std::unique_ptr<SO2Impl> m_impl;
};
