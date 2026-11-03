set(MPB_ROOT "${PROJECT_SOURCE_DIR}/third_party/mpb")
configure_file(config.h.in "${CMAKE_CURRENT_BINARY_DIR}/config.h")
set(MPB_HEADERS "${CMAKE_CURRENT_BINARY_DIR}/include")
file(MAKE_DIRECTORY "${MPB_HEADERS}/mpb")
foreach(header matrices/eigensolver.h matrices/matrices.h matrices/scalar.h
    maxwell/maxwell.h util/verbosity.h)
  get_filename_component(name "${header}" NAME)
  configure_file("${MPB_ROOT}/src/${header}" "${MPB_HEADERS}/mpb/${name}" COPYONLY)
endforeach()
file(READ "${MPB_ROOT}/src/mpbconf.h.in" public_header)
foreach(definition SCALAR_COMPLEX WITH_HERMITIAN_EPSILON MPB_VERSION_MAJOR MPB_VERSION_MINOR MPB_VERSION_PATCH)
  if(definition STREQUAL "MPB_VERSION_MAJOR")
    set(value 1)
  elseif(definition STREQUAL "MPB_VERSION_MINOR")
    set(value 12)
  elseif(definition STREQUAL "MPB_VERSION_PATCH")
    set(value 0)
  else()
    set(value 1)
  endif()
  string(REPLACE "#undef ${definition}\n" "#define ${definition} ${value}\n" public_header "${public_header}")
endforeach()
string(REPLACE "extern void (*mpb_printf_callback)(const char *s);"
  "#ifdef __cplusplus\nextern \"C\" {\n#endif\nextern void (*mpb_printf_callback)(const char *s);\n#ifdef __cplusplus\n}\n#endif"
  public_header "${public_header}")
file(CONFIGURE OUTPUT "${MPB_HEADERS}/mpb.h" CONTENT "${public_header}" @ONLY)
set(MPB_SOURCES
  util/debug_malloc.c util/mpi_utils.c util/verbosity.c
  matrices/blasglue.c matrices/eigensolver.c matrices/eigensolver_davidson.c
  matrices/eigensolver_utils.c matrices/evectmatrix.c matrices/linmin.c
  matrices/matrices.c matrices/minpack2-linmin.c matrices/sqmatrix.c
  maxwell/maxwell.c maxwell/maxwell_constraints.c maxwell/maxwell_eps.c
  maxwell/maxwell_op.c maxwell/maxwell_pre.c)
list(TRANSFORM MPB_SOURCES PREPEND "${MPB_ROOT}/src/")
add_library(mpb STATIC ${MPB_SOURCES})
target_include_directories(mpb PUBLIC "${MPB_HEADERS}" PRIVATE "${CMAKE_CURRENT_BINARY_DIR}"
  "${MPB_ROOT}/src/util" "${MPB_ROOT}/src/matrices" "${MPB_ROOT}/src/maxwell")
target_link_libraries(mpb PUBLIC meep_numerics)
