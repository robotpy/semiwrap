#pragma once

inline int CamelGetHTTPServer() { return 11; }
inline int camel_get_foo_value() { return 12; }
inline int SW_CamelPrefixedValue() { return 13; }

class NameTransformCamelCases {
public:
  int CamelGetHTTPServer() { return 14; }
  int camel_get_foo_value() { return 15; }
  int SW_CamelPrefixedValue() { return 16; }

  int CamelPublicValue = 17;
  int CamelHTTPServerValue = 18;
  int SW_CamelAttrValue = 19;
};

enum CamelTransformEnum {
  CamelTransformEnum_ValueOne = 41,
  CamelTransformEnumHTTPServer = 42,
  SW_CamelTransformEnumPrefixedValue = 43,
};
