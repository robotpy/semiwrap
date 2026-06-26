#include "case_test.h"

int makeHTTPServerValue() { return 11; }

CapsCaseThing::CapsCaseThing(int value) : publicHTTPValue(value + 10), value(value) {}

int CapsCaseThing::getHTTPServerValue() const { return value; }

int CapsCaseThing::addFooValue(int value) const { return this->value + value; }
