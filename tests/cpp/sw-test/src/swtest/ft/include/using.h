
#pragma once

#include "using_companion.h"
#include <string>

namespace cr::inner {

using cr2::WontResolve;
    
class ProtectedUsing {
public:

  ProtectedUsing() = default;
  virtual ~ProtectedUsing() = default;

protected:
  ProtectedUsing(CantResolve t) {}
};

class VirtualReturnProbe {
public:
  virtual ~VirtualReturnProbe() = default;
  virtual REVLibError setPosition(double position) { return 1; }
};

class ConfiguredAliasReturnProbe {
public:
  virtual ~ConfiguredAliasReturnProbe() = default;
  virtual ConfiguredAliasReturn getError() { return 1; }
};

inline void fn_using(AlsoCantResolve t) {}
inline void fn_using(std::string t) {}
inline REVLibError fn_lambda_return_probe(double position, int* status) {
  *status = static_cast<int>(position);
  return 1;
}

}

// used in using2.h
namespace u {

struct FwdDecl {
  int x = 0;
};

}