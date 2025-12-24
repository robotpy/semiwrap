
#include "int_with_offset.h"

int Unwrap(int_ns::IntWithOffset<0> value = int_ns::IntWithOffset<5>{5}) {
  return value.Get();
}
