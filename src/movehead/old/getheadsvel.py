#!/usr/bin/env python
import cv2
import rospy
from face_recognition_ros.msg import Heads, HeadsArray ###do i nead Heads?
from sensor_msgs.msg import Image
from cv_bridge import CvBridge, CvBridgeError
# import numpy as np

class HeadVel:
    def __init__(self):
        rospy.init_node('getvelheads_node', anonymous=True)
        flowy_topic = rospy.get_param('~flowx_topic','/df_node/flow_x')
        flowy_topic = rospy.get_param('~flowy_topic','/df_node/flow_y')

        rospy.loginfo('Input flow x topic being read as background image: {}'.format(flowx_topic))
        rospy.loginfo('Input flow y topic being read as background image: {}'.format(flowy_topic))

        self.hss =  rospy.Subscriber('heads', HeadsArray, self.updateheads)
        self.cvbridge = CvBridge()
        #maybe this is a good time for a wait_for_message; to initialize this thing correctly
        rospy.logdebug('waiting for flow topic to publish first image so I can initialize this guy ')
        self.bgxd = rospy.wait_for_message(flowx_topic, Image)
        self.bgyd = rospy.wait_for_message(flowy_topic, Image)
        self.issx = rospy.Subscriber(flowx_topic, Image, self.updatebgx)
        self.issy = rospy.Subscriber(flowx_topic, Image, self.updatebgy)

        self.hp = rospy.Publisher('newheads', HeadsArray, queue_size=1)
        self.ihpx = rospy.Publisher('newheads_imgx', Image, queue_size=1)
        self.ihpy = rospy.Publisher('newheads_imgy', Image, queue_size=1)

        # self.bg = np.array([],'uint8')

        HAC = HeadsArray()
        self.HA = HAC.heads ### this is just a list. i could initialize it to an empty list...
        rospy.loginfo('Headsvel initialized. ')
        myrate = rospy.Rate(10)
        while not rospy.is_shutdown():
            self.pubnewheads()
            myrate.sleep()

    def updatebgx(self,data):
        #rospy.logdebug('updatebg called')
        #self.bgx = self.cvbridge.imgmsg_to_cv2(data, 'bgr8')
        #maybe it makes sense to break pubnewheads into 2 and update them here and remove rate.
        self.bgxd = data
    def updatebgy(self,data):
        #rospy.logdebug('updatebg called')
        self.bgyd = data

    def updateheads(self,data):
        rospy.logdebug('updateheads called')
        self.HA = data.heads

    def pubnewheads(self):
        rospy.logdebug('pubnewheads called')
        #print(type(self.bg    ))
        bgx = self.cvbridge.imgmsg_to_cv2(self.bgxd, 'bgr8')
        bgy = self.cvbridge.imgmsg_to_cv2(self.bgyd, 'bgr8')
        for i in range(0, len(self.HA)):
            aHead = self.HA[i]
            myheadregionx = self.bgx[aHead.left:aHead.right,aHead.top:aHead.bottom]
            myheadregiony = self.bgy[aHead.left:aHead.right,aHead.top:aHead.bottom]
            ddx = myheadregionx.mean()-255/2
            ddy = myheadregiony.mean()-255/2
            self.HA[i].left   = (self.HA[i].left   + ddx).astype('uint8')
            self.HA[i].right  = (self.HA[i].right  + ddx).astype('uint8')
            self.HA[i].top    = (self.HA[i].top    + ddy).astype('uint8')
            self.HA[i].bottom = (self.HA[i].bottom + ddy).astype('uint8')
            if i == 0:
                self.ihpx.publish(self.cvbridge.cv2_to_imgmsg(myheadregionx,'mono8'))
                self.ihpy.publish(self.cvbridge.cv2_to_imgmsg(myheadregiony,'mono8'))
                #this is useless...
                #maybe it will be useful for debugging?; the real useful one would be the faces in rgb, if any..
            else:
                rospy.logwarn('more then one head! heads are still not ordered, so I will mess up!!!!')
        self.hp.publish(self.HA)

if __name__ == '__main__':

    sf = HeadVel()
