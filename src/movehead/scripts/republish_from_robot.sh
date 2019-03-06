#!/usr/bin/env bash

###erm, roslaunch much?
rosrun image_transport republish theora in:=camera/rgb/image_color raw out:=/rgb_from_robot_decompressed
