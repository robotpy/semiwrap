#pragma once

#ifdef SOMETHING_DEFINED

bool was_something_defined() { return true; }

#else

#error "Was not defined"

#endif
