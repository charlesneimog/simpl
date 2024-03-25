cmake_minimum_required(VERSION 3.5)
project(simpl)

#╭──────────────────────────────────────╮
#│              Libraries               │
#╰──────────────────────────────────────╯
add_subdirectory(src/loris)
set_target_properties(loris PROPERTIES LIBRARY_OUTPUT_DIRECTORY ${CMAKE_SOURCE_DIR})
set_target_properties(loris PROPERTIES POSITION_INDEPENDENT_CODE ON)

add_subdirectory(src/mq)
set_target_properties(mq PROPERTIES LIBRARY_OUTPUT_DIRECTORY ${CMAKE_SOURCE_DIR})
set_target_properties(mq PROPERTIES POSITION_INDEPENDENT_CODE ON)

add_subdirectory(src/sndobj)
set_target_properties(sndobj PROPERTIES LIBRARY_OUTPUT_DIRECTORY ${CMAKE_SOURCE_DIR})
set_target_properties(sndobj PROPERTIES POSITION_INDEPENDENT_CODE ON)

add_subdirectory(src/sms)
set_target_properties(sms PROPERTIES LIBRARY_OUTPUT_DIRECTORY ${CMAKE_SOURCE_DIR})
set_target_properties(sms PROPERTIES POSITION_INDEPENDENT_CODE ON)

#╭──────────────────────────────────────╮
#│                SIMPL                 │
#╰──────────────────────────────────────╯
file(GLOB SIMPL_SOURCES src/simpl/*.cpp)

add_library(simpl STATIC ${SIMPL_SOURCES})
set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} -std=c++03")

target_include_directories(simpl PUBLIC ${include_files})
target_link_libraries(simpl loris mq sndobj sms)

if(BUILD_TESTS)
    list(APPEND libs simpl cppunit sndfile)
    include_directories(tests)
    set(test_src tests/tests.cpp
                 tests/test_base.cpp
                 tests/test_peak_detection.cpp
                 tests/test_partial_tracking.cpp
                 tests/test_synthesis.cpp
                 tests/test_residual.cpp)

    add_executable(tests ${test_src})
    target_link_libraries(tests ${libs})
endif()
