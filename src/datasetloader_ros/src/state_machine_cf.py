#!/usr/bin/env python
import rospy
import smtt

if __name__ == '__main__':
    try:
        rospy.init_node('cfstatemachine_node', log_level=rospy.INFO)
        smtt.statemachine('cf')
        while not rospy.is_shutdown():
            rospy.spin()
    except rospy.ROSInterruptException:
        pass
