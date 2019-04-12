#!/usr/bin/env python
from __future__ import division
import cv2
import rospy
import threading
from face_recognition_ros.msg import HeadsFloat, HeadsArrayFloat ###do i nead Heads?
from sensor_msgs.msg import Image
from sensor_msgs.msg import CameraInfo
from cv_bridge import CvBridge, CvBridgeError
from copy import deepcopy

import numpy as np
import math

class HeadVel:
    def __init__(self):
        rospy.init_node('getvelheads_v4', anonymous=True)
        flowx_topic = rospy.get_param('~flowx_topic','/df_node/flow_xy')
        self.max_head_age = rospy.get_param('~max_head_age', 300) ## so follow for 10 seconds at 30 fps
        #I need the size of the image that was used to get the heads topic
        camerainfo = rospy.wait_for_message('/camera/rgb/camera_info', CameraInfo)
        print(camerainfo.height)
        print(camerainfo.width)
        self.height = camerainfo.height
        self.width = camerainfo.width

        rospy.loginfo('Input flow xy topic being read as background image: {}'.format(flowx_topic))

        self.hss =  rospy.Subscriber('heads', HeadsArrayFloat, self.updateheads)
        self.cvbridge = CvBridge()
        #maybe this is a good time for a wait_for_message; to initialize this thing correctly
        rospy.logdebug('waiting for flow topics to publish first image so I can initialize this guy ')
        self.bgxd = rospy.wait_for_message(flowx_topic, Image)

        ##now I need to get the size of the flow topics
        bgx = self.cvbridge.imgmsg_to_cv2(self.bgxd, 'bgr8')
        self.flowheight = bgx.shape[0]
        self.flowwidth = bgx.shape[1]
        rospy.loginfo('flow dims: {} x {}'.format(self.flowwidth,self.flowheight))
        self.wr = self.flowwidth /self.width
        self.hr = self.flowheight/self.height
        rospy.loginfo('transform rates: {} x {}'.format(self.wr,self.hr))

        self.issx = rospy.Subscriber(flowx_topic, Image, self.updatebgxy)

        self.hp = rospy.Publisher('newheads', HeadsArrayFloat, queue_size=1)
        self.hpf = rospy.Publisher('newheads_flow', HeadsArrayFloat, queue_size=1)

        self.ihpx = rospy.Publisher('newheads_imgxy', Image, queue_size=1)
        self.lock = threading.Lock()
        HAC = HeadsArrayFloat()
        self.HA = HAC.heads ### this is just a list. i could initialize it to an empty list...
        self.heads_age = 0 ### I am going to keep a counter to know how old the information about the head is and not try to follow it forever.
        rospy.loginfo('Headsvel initialized. ')
        while not rospy.is_shutdown():
            rospy.spin()

    def transformhead(self,aHead):
        rospy.logdebug('old head is:')
        rospy.logdebug(aHead)
        newhead = HeadsFloat()
        ### makes sure I am greater than zero and smaller than the flow dimensions.
        newhead.left    = min(max(0, (aHead.left    *self.wr)),self.flowwidth)
        newhead.right   = min(max(0, (aHead.right   *self.wr)),self.flowwidth)
        newhead.top     = min(max(0, (aHead.top     *self.hr)),self.flowheight)
        newhead.bottom  = min(max(0, (aHead.bottom  *self.hr)),self.flowheight)
        rospy.logdebug('new head is:')
        rospy.logdebug(newhead)
        return newhead

    def updateheads(self,data):
        rospy.logdebug('updateheads called')
        #might need a lock here too...
        with self.lock:
            self.HA = data.heads
            self.heads_age = 0 ## got new head!
            rospy.logdebug(self.HA)
            #rospy.logwarn(self.heads_age)

    def updatebgxy(self,data):
        with self.lock:
            thisAge = self.heads_age
        if thisAge < self.max_head_age:
            bg = self.cvbridge.imgmsg_to_cv2(data, 'bgr8')
            #rospy.logwarn(bg.shape)
            with self.lock:
                myha = deepcopy(self.HA)
                if not myha:
                    return
                #rospy.logwarn(myha)
            hf = []
            for i in range(0, len(myha)):
                aHead = myha[i]
                newhead = self.transformhead(aHead)
                hf.append(newhead)
                rospy.logdebug(bg.shape)
                myheadregion = bg[int(newhead.top):int(newhead.bottom), int(newhead.left):int(newhead.right)]
                rospy.logdebug(myheadregion.shape)
                #maybe I want to publish ddx?
                if myheadregion.shape[0]>0 and myheadregion.shape[1]>0: #only changes head if not size 0
                    avgs = np.average(np.average(myheadregion,axis=0), axis=0)
                    rospy.logdebug('mean value of region {}, {}'.format(avgs[0], avgs[1]))

                    ##there is a bunch of conversions here and I am not being careful this will break if images change!
                    ddxf = 0.2*(avgs[0]-127)
                    ddyf = 0.2*(avgs[1]-127)
                    ddx = ddxf/self.wr
                    ddy = ddyf/self.hr
                    rospy.logdebug('dx {}, dy {}'.format(ddx, ddy))
                    if not math.isnan(ddx):
                        myha[i].left   = min(max(0,(myha[i].left   - ddx)) ,self.width )
                        myha[i].right  = min(max(0,(myha[i].right  - ddx)) ,self.width )
                        newhead.left   = min(max(0,(newhead.left   - ddxf)),self.height)
                        newhead.right  = min(max(0,(newhead.right  - ddxf)),self.height)
                    if not math.isnan(ddy):
                        myha[i].top    = min(max(0,(myha[i].top    - ddy)) ,self.width )
                        myha[i].bottom = min(max(0,(myha[i].bottom - ddy)) ,self.width )
                        newhead.top    = min(max(0,(newhead.top    - ddyf)),self.height)
                        newhead.bottom = min(max(0,(newhead.bottom - ddyf)),self.height)
                    hf.append(newhead)
                    if i == 0:

                        #pass
                        self.ihpx.publish(self.cvbridge.cv2_to_imgmsg(myheadregion,'bgr8'))
                    else:
                        rospy.logwarn('more then one head! heads are still not ordered, so I will mess up!!!!')
                #rospy.signal_shutdown('damn it')
            #this however is not fine. probably needs a lock?
            #maybe I can get away with more speed if I write the controller to be threaded as well under pan and tilt
            self.hpf.publish(hf)
            with self.lock:
                self.HA = myha
                self.hp.publish(self.HA)
        else:
            rospy.logdebug('Head age limit reached. Not publishing new heads!')
        with self.lock:
            self.heads_age = self.heads_age + 1

if __name__ == '__main__':

    sf = HeadVel()
