#!/usr/bin/env python
import cv2
import rospy
from face_recognition_ros.msg import Heads, HeadsArray ###do i nead Heads?
from sensor_msgs.msg import Image
from cv_bridge import CvBridge, CvBridgeError
# import numpy as np

class ShowFace:
    def __init__(self):
        rospy.init_node('showheads_node', anonymous=True)
        image_topic = rospy.get_param('~image_topic','camera/rgb/image_color')
        rospy.loginfo('Input image topic being read as background image: {}'.format(image_topic))
        self.hss =  rospy.Subscriber('heads', HeadsArray, self.updateheads)
        self.cvbridge = CvBridge()
        #maybe this is a good time for a wait_for_message; to initialize this thing correctly
        rospy.logdebug('waiting for image topic to publish first image so I can initialize this guy ')
        self.bg = self.cvbridge.imgmsg_to_cv2( rospy.wait_for_message(image_topic, Image), 'bgr8')
        self.iss = rospy.Subscriber(image_topic, Image, self.updatebg)
        self.ipp = rospy.Publisher('heads_im', Image, queue_size=1)
        self.mainheadcolor = (0,255,0)
        self.otherheadscolor = (255,0,0)
        # self.bg = np.array([],'uint8')
        self.font = cv2.FONT_HERSHEY_SIMPLEX
        HAC = HeadsArray()
        self.HA = HAC.heads ### this is just a list. i could initialize it to an empty list...
        rospy.loginfo('ShowFace initialized. ')
        myrate = rospy.Rate(10)
        while not rospy.is_shutdown():
            self.pubimage()
            myrate.sleep()

    def updatebg(self,data):
        rospy.logdebug('updatebg called')
        self.bg = self.cvbridge.imgmsg_to_cv2(data, 'bgr8')

    def updateheads(self,data):
        rospy.logdebug('updateheads called')
        self.HA = data.heads

    def pubimage(self):
        rospy.logdebug('pubinfo called')
        #print(type(self.bg    ))
        firsthead = True
        for aHead in self.HA:
            if firsthead:
                headcolor = self.mainheadcolor
                headtext = '0'
                firsthead = False
            else:
                headcolor = self.otherheadscolor
                headtext = '?'
            cv2.rectangle(self.bg,(aHead.left,aHead.top),(aHead.right,aHead.bottom),headcolor,3)
            cv2.putText(self.bg,headtext,(aHead.left,aHead.bottom),self.font,1,(255,255,255))
        self.ipp.publish(self.cvbridge.cv2_to_imgmsg(self.bg,'bgr8'))

if __name__ == '__main__':

    sf = ShowFace()
