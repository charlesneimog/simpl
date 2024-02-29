cmake_minimum_required(VERSION 3.5)

project(rtharmonicsynthesis)

add_executable(rtharmonicsynthesis rtharmonicsynthesis.cpp)

# add ../src to the include path
include_directories(../src/simpl/)
include_directories(../src/mq/)
include_directories(../src/sms/)
include_directories(../src/loris/)
include_directories(../src/sndobj/)

# add ../build/ to the link path
link_directories(../build/)

find_package(Pipewire REQUIRED)
target_link_libraries(rtharmonicsynthesis simpl ${Pipewire_LIBRARIES})
target_include_directories(rtharmonicsynthesis PUBLIC ${Pipewire_INCLUDE_DIRS})


target_link_directories(rtharmonicsynthesis PUBLIC ../build)

target_link_libraries(rtharmonicsynthesis simpl)
