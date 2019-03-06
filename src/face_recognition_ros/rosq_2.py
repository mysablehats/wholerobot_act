#!/usr/bin/env python3

import rospy
from sensor_msgs.msg import Image
from cv_bridge import CvBridge, CvBridgeError
import numpy as np

rospy.init_node('blank_image')
image_pub = rospy.Publisher("image_raw",Image, queue_size=1)

bridge = CvBridge()
blank_image = np.zeros((200,600,3), np.uint8)

r = rospy.Rate(10)
try:
    while not rospy.is_shutdown():
        try:
            image_pub.publish(bridge.cv2_to_imgmsg(blank_image, "bgr8"))
        except CvBridgeError as e:
            print(e)
        r.sleep()
    rospy.spin()
except KeyboardInterrupt:
    print("Shutting down")
