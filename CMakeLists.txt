cmake_minimum_required(VERSION 3.26)
project(meep VERSION 1.35.0 LANGUAGES C CXX)

set(CMAKE_C_STANDARD 11)
set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_MSVC_RUNTIME_LIBRARY MultiThreadedDLL)
set(CMAKE_POSITION_INDEPENDENT_CODE ON)

option(MEEP_BUILD_PYTHON "Build the CPython extension" ON)
option(MEEP_BUILD_TESTS "Build native regression tests" ON)
option(MEEP_BUILD_EXAMPLES "Build the native Windows debugging example" ON)
option(MEEP_BUILD_SCHEME "Build the unsupported Scheme frontend" OFF)
option(MEEP_WITH_HARMINV "Enable resonance analysis" ON)
option(MEEP_WITH_MPB "Enable MPB eigenmodes" ON)
option(MEEP_WITH_MPI "Enable MPI (not ported yet)" OFF)
option(MEEP_WITH_OPENMP "Enable OpenMP (not ported yet)" OFF)
if(MEEP_BUILD_SCHEME OR MEEP_WITH_MPI OR MEEP_WITH_OPENMP)
  message(FATAL_ERROR "Scheme, MPI and OpenMP are not yet supported by this CMake port. See WINDOWS_PORTING_PLAN.md.")
endif()
if(MSVC)
  add_compile_definitions(_CRT_SECURE_NO_WARNINGS _USE_MATH_DEFINES NOMINMAX)
  add_compile_options(/utf-8 /bigobj "$<$<COMPILE_LANGUAGE:CXX>:/permissive->")
endif()
# Opening this folder in Visual Studio does not activate the development venv.
# Prefer it by default, while preserving an explicitly selected interpreter.
set(MEEP_VENV_ROOT "${CMAKE_CURRENT_SOURCE_DIR}/.venv" CACHE PATH "Meep development environment")
if(WIN32 AND NOT DEFINED Python_EXECUTABLE AND EXISTS "${MEEP_VENV_ROOT}/Scripts/python.exe")
  set(Python_EXECUTABLE "${MEEP_VENV_ROOT}/Scripts/python.exe" CACHE FILEPATH "Python interpreter")
endif()
if(MEEP_BUILD_PYTHON)
  find_package(Python REQUIRED COMPONENTS Interpreter Development.Module NumPy)
else()
  find_package(Python REQUIRED COMPONENTS Interpreter)
endif()
execute_process(COMMAND "${Python_EXECUTABLE}" -c "import sys; print(sys.prefix)"
  OUTPUT_VARIABLE MEEP_PYTHON_PREFIX OUTPUT_STRIP_TRAILING_WHITESPACE
  COMMAND_ERROR_IS_FATAL ANY)
message(STATUS "Meep Python environment: ${MEEP_PYTHON_PREFIX}")
file(TO_CMAKE_PATH "${MEEP_PYTHON_PREFIX}" MEEP_PYTHON_PREFIX)
if(MSVC)
  set(CMAKE_C_COMPILER_LAUNCHER "${Python_EXECUTABLE};${CMAKE_CURRENT_SOURCE_DIR}/tools/windows/cl_launcher.py")
  set(CMAKE_CXX_COMPILER_LAUNCHER "${CMAKE_C_COMPILER_LAUNCHER}")
  set(CMAKE_CL_SHOWINCLUDES_PREFIX "Note: including file: ")
endif()
include(cmake/MeepMKL.cmake)
configure_file(cmake/build-info.json.in "${CMAKE_CURRENT_BINARY_DIR}/meep-build-info.json" @ONLY)

# Keep HDF5 self-contained: C API, static /MD, no optional compression filters.
set(BUILD_SHARED_LIBS OFF CACHE BOOL "" FORCE)
set(BUILD_TESTING OFF CACHE BOOL "" FORCE)
set(HDF5_BUILD_CPP_LIB OFF CACHE BOOL "" FORCE)
set(HDF5_BUILD_FORTRAN OFF CACHE BOOL "" FORCE)
set(HDF5_BUILD_HL_LIB OFF CACHE BOOL "" FORCE)
set(HDF5_BUILD_TOOLS OFF CACHE BOOL "" FORCE)
set(HDF5_BUILD_EXAMPLES OFF CACHE BOOL "" FORCE)
set(HDF5_ENABLE_Z_LIB_SUPPORT OFF CACHE BOOL "" FORCE)
set(HDF5_ENABLE_SZIP_SUPPORT OFF CACHE BOOL "" FORCE)
set(HDF5_ENABLE_PARALLEL OFF CACHE BOOL "" FORCE)
set(HDF5_ENABLE_DEPRECATED_SYMBOLS ON CACHE BOOL "" FORCE)
add_subdirectory(third_party/hdf5 EXCLUDE_FROM_ALL)

set(MEEP_GENERATED "${CMAKE_CURRENT_BINARY_DIR}/generated")
file(MAKE_DIRECTORY "${MEEP_GENERATED}/meep")
include(CheckIncludeFileCXX)
include(CheckCXXSourceCompiles)
check_include_file_cxx(sys/time.h HAVE_SYS_TIME_H)
check_include_file_cxx(immintrin.h HAVE_IMMINTRIN_H)
check_cxx_source_compiles("int main(){_Pragma(\"ivdep\") for(int i=0;i<2;++i){}return 0;}" HAVE_CXX_PRAGMA)
set(HAVE_HDF5 1)
set(HAVE_LIBFFTW3 1)
set(HAVE_BLAS 1)
set(HAVE_LAPACK 1)
set(HAVE_CBLAS_DDOT 1)
set(HAVE_CBLAS_DAXPY 1)
set(HAVE_CTL_PRINTF_CALLBACK 1)
set(HAVE_MAKE_MESH_WITH_CENTER 1)
set(HAVE_HARMINV ${MEEP_WITH_HARMINV})
set(HAVE_MPB ${MEEP_WITH_MPB})
set(HAVE_MPB_PRINTF_CALLBACK ${MEEP_WITH_MPB})
configure_file(cmake/config.h.in "${MEEP_GENERATED}/config.h")
set(MEEP_SINGLE 0)
set(MEEP_SWIG_PYTHON_THREADS 0)
set(MEEP_SWIG_PYTHON_DEBUG 0)
configure_file(src/meep/meep-config.h.in "${MEEP_GENERATED}/meep/meep-config.h" @ONLY)

set(CTL_ROOT "${CMAKE_CURRENT_SOURCE_DIR}/third_party/libctl")
if(NOT EXISTS "${CTL_ROOT}/utils/ctlgeom-types.h")
  message(FATAL_ERROR "libctlgeom generated files missing; use the release tarball via tools/windows/fetch_sources.py")
endif()
add_library(ctlgeom STATIC
  "${CTL_ROOT}/utils/geom.c" "${CTL_ROOT}/utils/geom-ctl-io.c"
  "${CTL_ROOT}/src/ctl-math.c" "${CTL_ROOT}/src/integrator.c")
target_compile_definitions(ctlgeom PRIVATE LIBCTLGEOM)
target_include_directories(ctlgeom PUBLIC "${CTL_ROOT}/utils" "${CTL_ROOT}/src")

if(MEEP_WITH_HARMINV)
  add_subdirectory(cmake/harminv)
endif()
if(MEEP_WITH_MPB)
  add_subdirectory(cmake/mpb)
endif()

add_executable(meep_sphere_quad EXCLUDE_FROM_ALL src/sphere-quad.cpp)
add_custom_command(OUTPUT "${MEEP_GENERATED}/sphere-quad.h"
  COMMAND "${Python_EXECUTABLE}" "${CMAKE_CURRENT_SOURCE_DIR}/tools/windows/generate.py"
    sphere "$<TARGET_FILE:meep_sphere_quad>" "${MEEP_GENERATED}/sphere-quad.h"
  DEPENDS meep_sphere_quad tools/windows/generate.py VERBATIM)
add_custom_command(OUTPUT "${MEEP_GENERATED}/step_generic_stride1.cpp"
  COMMAND "${Python_EXECUTABLE}" "${CMAKE_CURRENT_SOURCE_DIR}/tools/windows/generate.py"
    stride "${CMAKE_CURRENT_SOURCE_DIR}/src/step_generic.cpp" "${MEEP_GENERATED}/step_generic_stride1.cpp"
  DEPENDS src/step_generic.cpp tools/windows/generate.py VERBATIM)
set(MEEP_CORE_SOURCES
  array_slice anisotropic_averaging bands boundaries bicgstab casimir cw_fields
  dft dft_ldos energy_and_flux fields fields_dump fix_boundary_sources loop_in_chunks
  h5fields h5file initialize integrate integrate2 material_data monitor mympi
  multilevel-atom near2far output_directory random sources step step_db stress
  structure structure_dump susceptibility time update_eh mpb update_pols vec
  step_generic meepgeom GDSIIgeom)
list(TRANSFORM MEEP_CORE_SOURCES PREPEND "src/")
list(TRANSFORM MEEP_CORE_SOURCES APPEND ".cpp")
add_library(meep_core STATIC ${MEEP_CORE_SOURCES} src/support/mt19937ar.c
  "${MEEP_GENERATED}/sphere-quad.h" "${MEEP_GENERATED}/step_generic_stride1.cpp")
add_dependencies(meep_core meep_runtime)
target_include_directories(meep_core PUBLIC
  "$<BUILD_INTERFACE:${MEEP_GENERATED}>" "$<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}/src>")
target_compile_definitions(meep_core PRIVATE HAVE_CONFIG_H)
target_link_libraries(meep_core PUBLIC ctlgeom meep_numerics hdf5-static)
if(MEEP_WITH_HARMINV)
  target_link_libraries(meep_core PUBLIC harminv)
endif()
if(MEEP_WITH_MPB)
  target_link_libraries(meep_core PUBLIC mpb)
endif()

if(MEEP_BUILD_EXAMPLES)
  add_executable(meep_debug_example examples/windows/minimal.cpp)
  target_link_libraries(meep_debug_example PRIVATE meep_core)
endif()

if(MEEP_BUILD_PYTHON)
  find_program(SWIG_EXECUTABLE NAMES swig4.0 swig
    HINTS "${MEEP_PYTHON_PREFIX}/Scripts" "${MEEP_PYTHON_PREFIX}/bin")
  find_package(SWIG REQUIRED)
  set(MEEP_PYTHON_DIR "${CMAKE_CURRENT_BINARY_DIR}/python/meep")
  file(MAKE_DIRECTORY "${MEEP_PYTHON_DIR}/adjoint")
  file(GLOB MEEP_PY_HEADERS CONFIGURE_DEPENDS src/*.hpp src/meep/*.hpp)
  add_custom_command(OUTPUT "${MEEP_GENERATED}/meep-python.cxx" "${MEEP_PYTHON_DIR}/__init__.py"
    COMMAND "${SWIG_EXECUTABLE}" -c++ -python -nofastunpack
      "-I${MEEP_GENERATED}" "-I${CMAKE_CURRENT_SOURCE_DIR}/src"
      "-I${CMAKE_CURRENT_SOURCE_DIR}/python" "-I${CTL_ROOT}/utils" "-I${CTL_ROOT}/src"
      "-I${CMAKE_CURRENT_BINARY_DIR}/cmake/mpb/include"
      -outdir "${MEEP_PYTHON_DIR}" -o "${MEEP_GENERATED}/meep-python.cxx"
      "${CMAKE_CURRENT_SOURCE_DIR}/python/meep.i"
    COMMAND "${Python_EXECUTABLE}" "${CMAKE_CURRENT_SOURCE_DIR}/tools/windows/generate.py"
      package "${MEEP_PYTHON_DIR}/meep.py" "${MEEP_PYTHON_DIR}/__init__.py"
    DEPENDS python/meep.i python/numpy.i python/vec.i python/meep-python.hpp
      python/typemap_utils.cpp ${MEEP_PY_HEADERS} "${MEEP_GENERATED}/config.h"
      tools/windows/generate.py pyproject.toml VERBATIM)
  Python_add_library(_meep MODULE WITH_SOABI "${MEEP_GENERATED}/meep-python.cxx")
  target_include_directories(_meep PRIVATE python libpympb)
  target_link_libraries(_meep PRIVATE meep_core Python::NumPy)
  set_target_properties(_meep PROPERTIES LIBRARY_OUTPUT_DIRECTORY "${MEEP_PYTHON_DIR}"
    RUNTIME_OUTPUT_DIRECTORY "${MEEP_PYTHON_DIR}")
  set(MEEP_PY_MODULES binary_partition_utils chunk_balancer geom simulation source
    timing_measurements visualization materials verbosity_mgr)
  foreach(module IN LISTS MEEP_PY_MODULES)
    configure_file("python/${module}.py" "${MEEP_PYTHON_DIR}/${module}.py" COPYONLY)
  endforeach()
  file(GLOB MEEP_ADJOINT_MODULES "${CMAKE_CURRENT_SOURCE_DIR}/python/adjoint/*.py")
  foreach(module IN LISTS MEEP_ADJOINT_MODULES)
    get_filename_component(name "${module}" NAME)
    configure_file("${module}" "${MEEP_PYTHON_DIR}/adjoint/${name}" COPYONLY)
  endforeach()
  install(TARGETS _meep
    LIBRARY DESTINATION meep COMPONENT Python
    RUNTIME DESTINATION meep COMPONENT Python)
  install(DIRECTORY "${MEEP_PYTHON_DIR}/" DESTINATION meep COMPONENT Python
    FILES_MATCHING PATTERN "*.py" PATTERN "meep.py" EXCLUDE
    PATTERN "__pycache__" EXCLUDE PATTERN ".libs" EXCLUDE)
  # Runtime and license come from the same standalone SDK selected above.
  add_custom_command(TARGET _meep POST_BUILD
    COMMAND "${CMAKE_COMMAND}" -E make_directory "${MEEP_PYTHON_DIR}/.libs"
    COMMAND "${CMAKE_COMMAND}" -E copy_if_different ${MEEP_MKL_RUNTIME} "${MEEP_PYTHON_DIR}/.libs"
    COMMAND_EXPAND_LISTS VERBATIM)
  install(FILES ${MEEP_MKL_RUNTIME} DESTINATION meep/.libs COMPONENT Python)
  install(FILES LICENSE COPYRIGHT DESTINATION meep/licenses COMPONENT Python)
  install(FILES third_party/libctl/COPYING DESTINATION meep/licenses/libctl COMPONENT Python)
  install(FILES third_party/hdf5/COPYING DESTINATION meep/licenses/hdf5 COMPONENT Python)
  install(FILES third_party/harminv/COPYING DESTINATION meep/licenses/harminv COMPONENT Python)
  install(FILES third_party/mpb/COPYING DESTINATION meep/licenses/mpb COMPONENT Python)
  install(FILES "${MEEP_MKL_LICENSE}" DESTINATION meep/licenses/onemkl COMPONENT Python)
  install(FILES ${MEEP_MKL_NOTICES} DESTINATION meep/licenses/onemkl COMPONENT Python)
endif()

if(MEEP_BUILD_TESTS)
  enable_testing()
  add_executable(meep_numeric_backend tests/windows/numeric_backend.cpp)
  target_link_libraries(meep_numeric_backend PRIVATE meep_numerics)
  add_dependencies(meep_numeric_backend meep_runtime)
  add_test(NAME backend.oneMKL COMMAND meep_numeric_backend)
  if(MEEP_BUILD_EXAMPLES)
    add_test(NAME example.windows COMMAND meep_debug_example)
  endif()
  foreach(test IN ITEMS test-prism test-mesh)
    add_executable("ctlgeom_${test}" "${CTL_ROOT}/utils/${test}.c")
    target_link_libraries("ctlgeom_${test}" PRIVATE ctlgeom)
    add_test(NAME "ctlgeom.${test}" COMMAND "ctlgeom_${test}")
  endforeach()
  set_property(TEST ctlgeom.test-prism APPEND PROPERTY ENVIRONMENT_MODIFICATION
    "LIBCTL_TEST_PRISM_SEED=set:1")
  foreach(test IN ITEMS one_dimensional h5test physical flux pml)
    add_executable("meep_${test}" "tests/${test}.cpp")
    target_link_libraries("meep_${test}" PRIVATE meep_core)
    add_test(NAME "core.${test}" COMMAND "meep_${test}")
  endforeach()
  if(MEEP_BUILD_PYTHON AND MEEP_WITH_MPB)
    add_test(NAME python.smoke COMMAND "${Python_EXECUTABLE}"
      "${CMAKE_CURRENT_SOURCE_DIR}/tools/windows/smoke.py")
    set_tests_properties(python.smoke PROPERTIES ENVIRONMENT_MODIFICATION
      "PYTHONPATH=set:${CMAKE_CURRENT_BINARY_DIR}/python;MPLBACKEND=set:Agg")
  endif()
  # CTest/Test Explorer must also work when VS was started from the desktop.
  get_property(MEEP_TESTS DIRECTORY PROPERTY TESTS)
  set_property(TEST ${MEEP_TESTS} APPEND PROPERTY ENVIRONMENT_MODIFICATION
    "PATH=path_list_prepend:${MEEP_MKL_RUNTIME_DIR}"
    "MKL_NUM_THREADS=set:1" "OMP_NUM_THREADS=set:1")
endif()
message(STATUS "Meep ${PROJECT_VERSION}: Python=${MEEP_BUILD_PYTHON}, Scheme=OFF, MKL=LP64/sequential, Harminv=${MEEP_WITH_HARMINV}, MPB=${MEEP_WITH_MPB}, MPI=OFF")
