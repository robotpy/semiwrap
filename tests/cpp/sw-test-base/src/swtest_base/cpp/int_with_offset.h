#pragma once

namespace int_ns {

template <int Offset>
struct IntWithOffset {
  IntWithOffset() = default;

  explicit IntWithOffset(int val) : val{val} {}

  template <int OtherOffset>
  /* implicit */ IntWithOffset(IntWithOffset<OtherOffset> other) : val{Offset - OtherOffset + other.Get()} {}

  int Get() const { return val; }

  void Set(int val) { this->val = val; }

 private:
  int val;
};

};
