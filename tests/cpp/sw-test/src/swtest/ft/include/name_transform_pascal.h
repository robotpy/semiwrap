#pragma once

inline int PascalGetHTTPServer() { return 21; }
inline int pascal_get_foo_value() { return 22; }
inline int SW_PascalPrefixedValue() { return 23; }

class NameTransformPascalCases {
public:
  int PascalGetHTTPServer() { return 24; }
  int pascal_get_foo_value() { return 25; }
  int SW_PascalPrefixedValue() { return 26; }

  int PascalPublicValue = 27;
  int PascalHTTPServerValue = 28;
  int SW_PascalAttrValue = 29;
};

enum PascalTransformEnum {
  PascalTransformEnum_ValueOne = 51,
  PascalTransformEnumHTTPServer = 52,
  SW_PascalTransformEnumPrefixedValue = 53,
};
