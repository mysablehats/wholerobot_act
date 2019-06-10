#!/usr/bin/env python
import cv2
import rospy
from sensor_msgs.msg import Image
from geometry_msgs.msg import Polygon
from cv_bridge import CvBridge, CvBridgeError
# import numpy as np

class ShowFace:
    def __init__(self):
        rospy.init_node('showskel_node', anonymous=True)
        image_topic = 'im_in'# rospy.get_param('~image_topic','camera/rgb/image_color')
        rospy.loginfo('Input image topic being read as background image: {}'.format(image_topic))
        self.hss =  rospy.Subscriber('my_topic', Polygon, self.updateskel)
        self.cvbridge = CvBridge()
        #maybe this is a good time for a wait_for_message; to initialize this thing correctly
        rospy.logdebug('waiting for image topic to publish first image so I can initialize this guy ')
        self.bg = self.cvbridge.imgmsg_to_cv2( rospy.wait_for_message(image_topic, Image), 'bgr8')
        self.iss = rospy.Subscriber(image_topic, Image, self.updatebg)
        self.ipp = rospy.Publisher('skels_im', Image, queue_size=1)
        self.mainskelcolor = (0,255,0)
        self.otherskelscolor = (255,0,0)
        # self.bg = np.array([],'uint8')
        self.font = cv2.FONT_HERSHEY_SIMPLEX
        SK = Polygon()
        self.SK = SK.points ### this is just a list. i could initialize it to an empty list...
        rospy.loginfo('ShowFace initialized. ')
        myrate = rospy.Rate(10)
        while not rospy.is_shutdown():
            self.pubimage()
            myrate.sleep()

    def updatebg(self,data):
        rospy.logdebug('updatebg called')
        self.bg = self.cvbridge.imgmsg_to_cv2(data, 'bgr8')

    def updateskel(self,data):
        rospy.logdebug('updateskel called')
        self.SK = data.points

    def pubimage(self):
        rospy.logdebug('pubinfo called')
        #print(type(self.bg    ))
        # firstskel = True
        for a,aPoint in enumerate(self.SK):
            # if firstskel:
            #     skelcolor = self.mainskelcolor
            #     skeltext = '0'
            #     firstskel = False
            # else:
            #     skelcolor = self.otherskelscolor
            #     skeltext = '?'
            skeltext = str(a)
            skelcolor = self.mainskelcolor
            cv2.rectangle(self.bg,(int(aPoint.x-10),int(aPoint.y-10)),(int(aPoint.x+10),int(aPoint.y+10)),skelcolor,3)
            cv2.putText(self.bg,skeltext,(int(aPoint.x),int(aPoint.y)),self.font,1,(255,255,255))
        self.ipp.publish(self.cvbridge.cv2_to_imgmsg(self.bg,'bgr8'))

if __name__ == '__main__':

    sf = ShowFace()
