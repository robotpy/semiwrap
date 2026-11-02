#pragma once

#include <string>
#include <vector>

struct Reading {
  int channel;
  double value;
  bool valid;
};

class ReprClass {
public:
  int value = 4;
};

struct ReprRenamed {
  int first = 1;
  int ignored = 99;
  inline static int count = 100;
  std::string text = "hello";
  bool last = true;
};

struct ReprNested {
  Reading reading{2, 3.5, true};
  std::vector<int> values{1, 2};
};

struct ReprArray {
  int value = 1;
  int samples[1 + 1] = {2, 3};
};

struct ReprEmpty {};
struct ReprDisabled { int value = 1; };
struct ReprCustom { int value = 1; };
struct ReprGlobalCustom { int value = 1; };

struct ReprMethod {
  int value = 1;
  int method() { return value; }
};
struct ReprConstructor {
  int value;
  ReprConstructor() : value(1) {}
};
struct ReprDestructor {
  int value = 1;
  ~ReprDestructor() = default;
};
struct ReprDerived : ReprClass { int other = 2; };
struct ReprPrivate {
  int value = 1;
private:
  int hidden = 2;
};

struct ReprNode {
  ReprNode *next = nullptr;
};

struct ReprOuter {
  struct Inner { int value = 5; };
};

template <typename T>
struct ReprTemplate { T value{}; };

template <typename T>
struct ReprTemplateCustom { T value{}; };
