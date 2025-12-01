#pragma once

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