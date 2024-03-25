cmake_minimum_required(VERSION 3.5)
project(simpl)

#╭──────────────────────────────────────╮
#│              Libraries               │
#╰──────────────────────────────────────╯
add_subdirectory(src/loris)
add_subdirectory(src/mq)
add_subdirectory(src/sndobj)
add_subdirectory(src/sms)

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
