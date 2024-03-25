cmake_minimum_required(VERSION 3.25)
project(sndobj)

file(GLOB SNDOBJ_SOURCES ./*.cpp)
add_library(sndobj STATIC ${SNDOBJ_SOURCES})

target_include_directories(sndobj PUBLIC ${CMAKE_CURRENT_SOURCE_DIR})
