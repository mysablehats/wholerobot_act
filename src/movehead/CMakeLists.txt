cmake_minimum_required(VERSION 2.8.3)
project(movehead)

find_package(catkin REQUIRED COMPONENTS
  roscpp
  genmsg
  sensor_msgs
  actionlib
  actionlib_msgs
)

add_message_files(
  FILES
  Heads.msg
  HeadsArray.msg
)

## Generate actions in the 'action' folder
add_action_files(DIRECTORY action
   FILES
   PtuGoto.action
   PtuReset.action
   PtuSetVel.action
 )

  generate_messages(
    DEPENDENCIES
    actionlib_msgs
    sensor_msgs
    #std_msgs  # Or other packages containing msgs
  )

 catkin_package(
 #  INCLUDE_DIRS include
 #  LIBRARIES movehead
   CATKIN_DEPENDS roscpp message_runtime
   #other_catkin_pkg
 #  DEPENDS system_lib
 )

###########
## Build ##
###########

## Specify additional locations of header files
## Your package locations should be listed before other locations
include_directories(
  include
  ${catkin_INCLUDE_DIRS}
)

add_executable(${PROJECT_NAME}_test_node src/test.cpp)
add_dependencies(${PROJECT_NAME}_test_node ${${PROJECT_NAME}_EXPORTED_TARGETS} ${catkin_EXPORTED_TARGETS}
${PROJECT_NAME}_generate_messages_cpp
)
target_link_libraries(${PROJECT_NAME}_test_node
   ${catkin_LIBRARIES}
 )
