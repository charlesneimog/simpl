cmake_minimum_required(VERSION 3.25)
project(loris)

add_definitions(-DHAVE_FFTW3_H)

file(GLOB LORIS_SOURCES ./*.C)
add_library(loris STATIC ${LORIS_SOURCES})

set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} -std=c++03")

target_include_directories(loris PUBLIC ./)
target_link_libraries(loris fftw3)







