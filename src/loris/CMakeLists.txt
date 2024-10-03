cmake_minimum_required(VERSION 3.25)
project(loris)

add_definitions(-DHAVE_FFTW3_H)

file(GLOB LORIS_SOURCES ./*.C)
add_library(loris STATIC ${LORIS_SOURCES})

target_include_directories(loris PUBLIC ./)
target_link_libraries(loris fftw3)
target_compile_options(loris PRIVATE -std=c++03)
