#!/usr/bin/env python
import cv2
import rospy
from sensor_msgs.msg import Image
from geometry_msgs.msg import Polygon
from std_msgs.msg import Float32MultiArray
from cv_bridge import CvBridge, CvBridgeError
# import numpy as np
from copy import deepcopy

class MyPoint:
    def __init__(self):
        self.x = None
        self.y = None
        self.z = None

        self.confidence = None

class ShowSkel:
    def __init__(self,polyOrArr):
        rospy.init_node('showskel_node', anonymous=True, log_level=rospy.DEBUG)
        image_topic = 'im_in'# rospy.get_param('~image_topic','camera/rgb/image_color')
        rospy.loginfo('Input image topic being read as background image: {}'.format(image_topic))
        if polyOrArr == 'poly':
            self.hss =  rospy.Subscriber('my_topic', Polygon, self.updateskelPoly)
            self.SK = []
            Polygon()
            self.SK.append(SK.points) ### this is just a list. i could initialize it to an empty list...
        elif polyOrArr == 'array':
            self.hss =  rospy.Subscriber('skel', Float32MultiArray, self.updateskelArray)
            self.SK = []
        self.cvbridge = CvBridge()
        #maybe this is a good time for a wait_for_message; to initialize this thing correctly
        rospy.logdebug('waiting for image topic to publish first image so I can initialize this guy ')
        self.bg = self.cvbridge.imgmsg_to_cv2( rospy.wait_for_message(image_topic, Image), 'bgr8')
        self.bgstack = []
        self.bgstacksize = rospy.get_param('~bgstacksize',20) ### adjust this to the amount of delay we have. 
        assert self.bgstacksize > 1
        self.iss = rospy.Subscriber(image_topic, Image, self.updatebg)
        self.ipp = rospy.Publisher('skels_im', Image, queue_size=1)
        self.mainskelcolor = (0,255,0)
        self.otherskelscolor = (255,0,0)
        # self.bg = np.array([],'uint8')
        self.font = cv2.FONT_HERSHEY_SIMPLEX

        rospy.loginfo('ShowSkel initialized. ')
        self.markersize = 10
        self.myrate = rospy.Rate(10)

        self.numpersons = 1
        self.numbodyparts = 18

    def run(self):
        rospy.loginfo('Running. ')
        while not rospy.is_shutdown():
            self.pubimage()
            self.myrate.sleep()

    def updatebg(self,data):
        # rospy.logdebug('updatebg called')
        ###let's keep a stack of N frames
        self.bgstack.append(self.cvbridge.imgmsg_to_cv2(data, 'bgr8'))
        if len(self.bgstack) > self.bgstacksize:
            self.bgstack.pop(0)
        self.bg = self.bgstack[0]
        # self.bg = self.cvbridge.imgmsg_to_cv2(data, 'bgr8')

    def updateskelPoly(self,data):
        # rospy.logdebug('updateskelPoly called')
        self.SK = data.points

    def updateskelArray(self,data):
        # rospy.logdebug('updateskelArray called')
        ###not flexible. needs to have person, bodyparts and xyconfidence:
        for dimi in data.layout.dim:
            if dimi.label == 'person':
                self.numpersons = dimi.size
                rospy.logdebug('persons: %d'%self.numpersons)
                # rospy.logdebug(type(self.numpersons))
            if dimi.label == 'bodyparts':
                self.numbodyparts = dimi.size
                self.personstride = dimi.stride
                # rospy.logdebug(self.numbodyparts)
                # rospy.logdebug(type(self.numbodyparts))
                # rospy.logdebug(self.personstride)
                # rospy.logdebug(type(self.personstride))
            if dimi.label == 'xyconfidence':
                self.xyconfidence = dimi.size
                # rospy.logdebug(self.xyconfidence)
                # rospy.logdebug(type(self.xyconfidence))
                assert self.xyconfidence == 3 ##it has to be 3.

        self.SK = []
        debugnumpeople = 0
        for Nperson in range(self.numpersons):
            personchunkstart =   int(Nperson*self.personstride)
            # rospy.logdebug(personchunkstart)
            thisPersonData = data.data[personchunkstart:personchunkstart+self.personstride]
            thisPerson = []
            for bodypart in range(self.numbodyparts):
                thisBodypart = MyPoint()
                thisBodypart.x =            thisPersonData[bodypart*self.xyconfidence]
                thisBodypart.y =            thisPersonData[bodypart*self.xyconfidence+1]
                thisBodypart.confidence =   thisPersonData[bodypart*self.xyconfidence+2]
                thisPerson.append(thisBodypart)
            self.SK.append(deepcopy(thisPerson))
            debugnumpeople +=1
            rospy.logdebug('added a person %d'%debugnumpeople)
        # rospy.loginfo(self.SK)
    def pubimage(self):
        # rospy.logdebug('pubinfo called')
        debugnumpeople = 0
        #print(type(self.bg    ))
        firstskel = True
        if self.SK:
            for persons in self.SK:
                if firstskel:
                    skelcolor = self.mainskelcolor
                #     skeltext = '0'

                    firstskel = False
                else:
                    # rospy.logwarn('tanin')
                    skelcolor = self.otherskelscolor
            # for a,aPoint in enumerate(self.SK[0]):
                # rospy.logdebug(persons)
                for a,aPoint in enumerate(persons):

                         #skeltext = '?'
                    skeltext = str(a)
                    # skelcolor = self.mainskelcolor
                    cv2.rectangle(self.bg,(int(aPoint.x-self.markersize),int(aPoint.y-self.markersize)),(int(aPoint.x+self.markersize),int(aPoint.y+self.markersize)),skelcolor,1)
                    cv2.putText(self.bg,skeltext,(int(aPoint.x),int(aPoint.y)),self.font,0.5,(255,255,255))
                debugnumpeople +=1
                # rospy.logdebug('drawn a person %d'%debugnumpeople)

            self.ipp.publish(self.cvbridge.cv2_to_imgmsg(self.bg,'bgr8'))

if __name__ == '__main__':

    sf = ShowSkel('array')
    sf.run()
