#pragma once

inline int SnakeGetHTTPServer() { return 1; }
inline int snake_get_foo_value() { return 2; }
inline int SW_SnakePrefixedValue() { return 3; }

class NameTransformSnakeCases {
public:
  int SnakeGetHTTPServer() { return 4; }
  int snake_get_foo_value() { return 5; }
  int SW_SnakePrefixedValue() { return 6; }

  int SnakePublicValue = 7;
  int SnakeHTTPServerValue = 8;
  int SW_SnakeAttrValue = 9;
};

enum SnakeTransformEnum {
  SnakeTransformEnum_ValueOne = 31,
  SnakeTransformEnumHTTPServer = 32,
  SW_SnakeTransformEnumPrefixedValue = 33,
};

inline int SnakeRenameFunction() { return 34; }

enum SnakeRenameEnum {
  SnakeRenameEnum_Value = 35,
};

class NameTransformSnakeRenameCases {
public:
  int SnakeRenameMethod() { return 36; }
  int SnakeRenameAttribute = 37;
};
