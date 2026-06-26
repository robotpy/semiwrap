#pragma once

int makeHTTPServerValue();

class CapsCaseThing {
public:
  explicit CapsCaseThing(int value);

  int getHTTPServerValue() const;
  int addFooValue(int value) const;

  int publicHTTPValue;

private:
  int value;
};

enum CapsCaseEnum {
  CapsCaseEnumValueOne = 21,
  CapsCaseEnumHTTPServer = 22,
  CapsCaseEnumPrefixedValue = 23,
};
