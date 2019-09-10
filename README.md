# ROSMASTER package

This package contains the general state machine and packages necessary to launch the different ROS docker containers. 

This used to be deployed on the robot, but issues with Hydro made us use a different computer for ROSMASTER and leave only low-level IO related functions to be executed by the robot's PC. 

## TODO

- this should probably be split into sub-packages and dependencies made explicit
- remove FLIR driver as this is no longer in use
