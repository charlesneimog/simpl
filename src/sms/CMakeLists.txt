cmake_minimum_required(VERSION 3.25)
project(sms)

file(GLOB SMS_SOURCES ./*.c)
add_library(sms STATIC ${SMS_SOURCES})
target_link_libraries(sms fftw3 gsl)

target_include_directories(sms PUBLIC ${CMAKE_CURRENT_SOURCE_DIR})
