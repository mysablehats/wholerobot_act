#!/usr/bin/env python
from __future__ import division
import cv2
import rospy
import threading
from face_recognition_ros.msg import Heads, HeadsArray ###do i nead Heads?
from sensor_msgs.msg import Image
from sensor_msgs.msg import CameraInfo
from cv_bridge import CvBridge, CvBridgeError
from copy import deepcopy

#import numpy as np

class HeadVel:
    def __init__(self):
        rospy.init_node('getvelheads_v2', anonymous=True)
        flowx_topic = rospy.get_param('~flowx_topic','/df_node/flow_x')
        flowy_topic = rospy.get_param('~flowy_topic','/df_node/flow_y')

        #I need the size of the image that was used to get the heads topic
        camerainfo = rospy.wait_for_message('/camera/rgb/camera_info', CameraInfo)
        print(camerainfo.height)
        print(camerainfo.width)
        self.height = camerainfo.height
        self.width = camerainfo.width

        rospy.loginfo('Input flow x topic being read as background image: {}'.format(flowx_topic))
        rospy.loginfo('Input flow y topic being read as background image: {}'.format(flowy_topic))

        self.hss =  rospy.Subscriber('heads', HeadsArray, self.updateheads)
        self.cvbridge = CvBridge()
        #maybe this is a good time for a wait_for_message; to initialize this thing correctly
        rospy.logdebug('waiting for flow topics to publish first image so I can initialize this guy ')
        self.bgxd = rospy.wait_for_message(flowx_topic, Image)
        self.bgyd = rospy.wait_for_message(flowy_topic, Image)
        ##now I need to get the size of the flow topics
        bgx = self.cvbridge.imgmsg_to_cv2(self.bgxd, 'bgr8')
        self.flowheight = bgx.shape[0]
        self.flowwidth = bgx.shape[1]
        rospy.loginfo('flow dims: {} x {}'.format(self.flowwidth,self.flowheight))
        self.wr = self.flowwidth /self.width
        self.hr = self.flowheight/self.height
        rospy.loginfo('transform rates: {} x {}'.format(self.wr,self.hr))

        self.issx = rospy.Subscriber(flowx_topic, Image, self.updatebgx)
        self.issy = rospy.Subscriber(flowy_topic, Image, self.updatebgy)

        self.hp = rospy.Publisher('newheads', HeadsArray, queue_size=1)
        self.ihpx = rospy.Publisher('newheads_imgx', Image, queue_size=1)
        self.ihpy = rospy.Publisher('newheads_imgy', Image, queue_size=1)
        self.lock = threading.Lock()
        HAC = HeadsArray()
        self.HA = HAC.heads ### this is just a list. i could initialize it to an empty list...
        rospy.loginfo('Headsvel initialized. ')
        while not rospy.is_shutdown():
            rospy.spin()

    def transformhead(self,aHead):
        rospy.loginfo('old head is:')
        rospy.logwarn(aHead)
        newhead = Heads()
        newhead.left    = int(aHead.left    *self.wr)
        newhead.right   = int(aHead.right   *self.wr)
        newhead.top     = int(aHead.top     *self.hr)
        newhead.bottom  = int(aHead.bottom  *self.hr)
        rospy.loginfo('new head is:')
        rospy.logwarn(newhead)
        return newhead

    def updatebgx(self,data):
        #try:
        self.updatebgxy(True,data)
        #except:
        #    pass
    def updatebgy(self,data):
        try:
            self.updatebgxy(False,data)
        except:
            pass
    def updateheads(self,data):
        rospy.logdebug('updateheads called')
        #might need a lock here too...
        with self.lock:
            self.HA = data.heads
            rospy.logwarn(self.HA)

    def updatebgxy(self,isx,data):
        bg = self.cvbridge.imgmsg_to_cv2(data, 'mono8')
        #rospy.logwarn(bg.shape)
        with self.lock:
            myha = deepcopy(self.HA)
            if not myha:
                return
            #rospy.logwarn(myha)
        for i in range(0, len(myha)):
            aHead = myha[i]
            newhead = self.transformhead(aHead)
            rospy.logwarn(bg.shape)
            myheadregion = bg[newhead.left:newhead.right,newhead.top:newhead.bottom]
            rospy.logwarn(myheadregion.shape)
            #maybe I want to publish ddx?
            rospy.logwarn('mean value of region {}'.format(myheadregion.mean()))

            if isx:
                ##there is a bunch of conversions here and I am not being careful this will break if images change!
                ddx = (myheadregion.mean()-127)/self.wr
                rospy.logwarn(ddx)
                myha[i].left   = int(myha[i].left   + ddx)
                myha[i].right  = int(myha[i].right  + ddx)
                if i == 0:
                    self.ihpx.publish(self.cvbridge.cv2_to_imgmsg(myheadregion,'mono8'))
                else:
                    rospy.logwarn('more then one head! heads are still not ordered, so I will mess up!!!!')
            else:
                ddy = (myheadregion.mean()-127)/self.hr
                rospy.logwarn(ddy)
                myha[i].top    = int(myha[i].top    + ddy)
                myha[i].bottom = int(myha[i].bottom + ddy)
                if i == 0:
                    self.ihpy.publish(self.cvbridge.cv2_to_imgmsg(myheadregion,'mono8'))
                else:
                    rospy.logwarn('more then one head! heads are still not ordered, so I will mess up!!!!')
            rospy.logwarn(myha[i])
            #rospy.signal_shutdown('damn it')
        #this however is not fine. probably needs a lock?
        #maybe I can get away with more speed if I write the controller to be threaded as well under pan and tilt
        with self.lock:
            self.HA = myha
            self.hp.publish(self.HA)


if __name__ == '__main__':

    sf = HeadVel()
