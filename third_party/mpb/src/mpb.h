/* src/mpbconf.h.  Generated from mpbconf.h.in by configure.  */
#ifndef MPB_H
#define MPB_H 1

#define SCALAR_COMPLEX 1
/* #undef SCALAR_LONG_DOUBLE_PREC */
/* #undef SCALAR_SINGLE_PREC */
#define WITH_HERMITIAN_EPSILON 1
#define MPB_VERSION_MAJOR 1
#define MPB_VERSION_MINOR 12
#define MPB_VERSION_PATCH 0

#define MPB_REAL 1 /* avoid C++ conflict with MPB's "real" type */
#include "mpb/eigensolver.h"
#include "mpb/maxwell.h"
#include "mpb/verbosity.h"

extern void (*mpb_printf_callback)(const char *s);
#endif /* MPB_H */
