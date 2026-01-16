#pragma once

struct RefParam {
    int x = 1;
};

void fnParamObjRefOut(int x, RefParam &r) {
    r.x = x;
}
