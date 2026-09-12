# ULTRONE C++/CUDA Performance Modules - CMake Build
cmake_minimum_required(VERSION 3.18)
project(ultrone_cpp VERSION 1.0.0 LANGUAGES CXX)

# C++ standard
set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# Find Python and pybind11
find_package(Python COMPONENTS Interpreter Development REQUIRED)
find_package(pybind11 CONFIG REQUIRED)

# CUDA support (optional)
include(CheckLanguage)
check_language(CUDA)
if(CMAKE_CUDA_COMPILER)
    enable_language(CUDA)
    set(CMAKE_CUDA_STANDARD 17)
    message(STATUS "CUDA support enabled")
else()
    message(STATUS "CUDA not found - building CPU-only modules")
endif()

# Output directory
set(CMAKE_LIBRARY_OUTPUT_DIRECTORY ${CMAKE_BINARY_DIR}/ultrone_cpp)

# === Core performance module (CPU) ===
pybind11_add_module(ultrone_core
    src/core/performance_kernels.cpp
    src/core/parallel_pathfinding.cpp
    src/core/tensor_operations.cpp
)
target_include_directories(ultrone_core PRIVATE include)
set_target_properties(ultrone_core PROPERTIES OUTPUT_NAME ultrone_core)

# === CUDA module (if available) ===
if(CMAKE_CUDA_COMPILER)
    pybind11_add_module(ultrone_cuda
        src/cuda/cuda_kernels.cu
        src/cuda/cuda_bindings.cpp
    )
    target_include_directories(ultrone_cuda PRIVATE include)
    set_target_properties(ultrone_cuda PROPERTIES
        CUDA_SEPARABLE_COMPILATION ON
        OUTPUT_NAME ultrone_cuda
    )
endif()

# Install
install(TARGETS ultrone_core DESTINATION ultrone_cpp)
if(CMAKE_CUDA_COMPILER)
    install(TARGETS ultrone_cuda DESTINATION ultrone_cpp)
endif()