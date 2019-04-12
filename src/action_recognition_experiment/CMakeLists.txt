cmake_minimum_required(VERSION 2.8.3)
project(action_recognition_experiment)

find_package(catkin REQUIRED COMPONENTS
roscpp
rospy
cv_bridge
image_transport
message_generation
#std_msgs
std_srvs)

find_package(OpenCV)

add_service_files(
   FILES
   Actname.srv
)

generate_messages(
   DEPENDENCIES
   std_srvs
#   std_msgs
)

catkin_package(
# DEPENDS std_msgs
)

include_directories(
${catkin_INCLUDE_DIRS}
${OpenCV_INCLUDE_DIRS}
)

add_executable(vid src/video_recorder_srv.cpp)
add_dependencies(vid ${catkin_EXPORTED_TARGETS} action_recognition_experiment_generate_messages_cpp)
target_link_libraries(vid
  ${catkin_LIBRARIES} ${OpenCV_LIBRARIES}
)
