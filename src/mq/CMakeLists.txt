cmake_minimum_required(VERSION 3.25)
project(mq)

file(GLOB MQ_SOURCES ./*.cpp)
add_library(mq STATIC ${MQ_SOURCES})

target_link_libraries(mq fftw3)
target_include_directories(mq PUBLIC ../simpl/)
target_include_directories(mq PUBLIC ${CMAKE_CURRENT_SOURCE_DIR})










