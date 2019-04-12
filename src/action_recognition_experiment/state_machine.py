#!/usr/bin/env python
import rospy
import rosparam
import time
import os
from datasetloader_ros.srv import *
from std_srvs.srv import Empty
from std_msgs.msg import String
from sensor_msgs.msg import Image
#import os
import subprocess
import cv2
from cv_bridge import CvBridge, CvBridgeError
import numpy as np
from copy import deepcopy
from caffe_tsn_ros.msg import ActionDic
from threading import Lock
import pickle
from action_recognition_experiment.srv import Actname

DOSAY = False


class Test():
    pass

class Say():
    def __init__(self,saywhat):
        self.saywhat = saywhat
        if DOSAY:
            self.srvtopic = rospy.ServiceProxy("/play/%s"%saywhat, Empty)
        else:
            rospy.logwarn('DOSAY is False, not saying anything.')
            self.srvtopic = []

    def __call__(self):
        if DOSAY:
            rospy.loginfo('Saying: %s'%self.saywhat)
            self.srvtopic()
        else:
            rospy.logwarn('DOSAY is False, not saying anything.')
            rospy.logwarn('Would have said: %s'%self.saywhat)

class statemachine():
    def __init__(self):
        self.imp = []
        rospy.on_shutdown(self.myhook)
        global DOSAY
        try:
            rospy.wait_for_service('play/intro',timeout=1)
            DOSAY = True
        except:
            rospy.logwarn('bad_speech services do not seem to be running. will work without voice!')
        #check if activity recognition node is alive
        while rosparam.get_param('/rgb1/class_tsn_rgb/alive') is not 1:
            time.sleep(1)
        rospy.loginfo('tsn_caffe is alive. starting')
        start_act = rospy.ServiceProxy('/rgb1/start_vidscores', Empty)
        stop_act = rospy.ServiceProxy('/rgb1/stop_vidscores', Empty)
        start_color_rec = rospy.ServiceProxy('/rec_color/rec', Empty)
        stop_color_rec = rospy.ServiceProxy('/rec_color/stop', Empty)
        setname_color_rec = rospy.ServiceProxy('/rec_color/set_name', Actname)

        rospy.Subscriber('/rgb1/action_own_label',String,self.getslatest_activity,queue_size=1)
        rospy.Subscriber('/rgb1/action_own_label_dic',ActionDic,self.getslatest_activityDIC,queue_size=1)

        usewebcam = False
        try:
            RECORDDEPTH = rospy.get_param('~record_depth')
        except:
            RECORDDEPTH = False
            for listy in rospy.get_published_topics():
                for items in listy:
                     if 'depth' in items:
                         RECORDDEPTH = True
                         start_depth_rec = rospy.ServiceProxy('/rec_depth/rec', Empty)
                         stop_depth_rec = rospy.ServiceProxy('/rec_depth/stop', Empty)
                         setname_depth_rec = rospy.ServiceProxy('/rec_depth/set_name', Actname)

                     if 'webcam' in items:
                         usewebcam = True
        if usewebcam:
            rospy.logwarn('you seem to be using a webcam. will not try to record DEPTH')

        if not RECORDDEPTH and not usewebcam:
            rospy.logerr('don''t know what your input is' )

        testdir = "/mnt/externaldrive/var/datasets/test/"
        fps = 30
        self.testtimedir = testdir+time.strftime("%Y%m%d-%H%M%S",time.gmtime())
        os.mkdir(self.testtimedir)
        os.mkdir(os.path.join(self.testtimedir,'depth'))
        os.mkdir(os.path.join(self.testtimedir,'image'))
        self.dic = []
        self.actact = []
        self.imp = rospy.Publisher('/screen',Image, queue_size=1)
        self.bridge = CvBridge()
        self.font = cv2.FONT_HERSHEY_SIMPLEX
        self.background = np.zeros((720,1440,3),np.uint8)
        self.image = deepcopy(self.background)
        self.r = 30
        self.myrate = rospy.Rate(self.r)
        self.mylock = Lock()
        #while not rospy.is_shutdown():
        self.writetext('Hello World',1)
        helloserv = Say('hello_world')
        helloserv()

        #    a.sleep()
        time.sleep(3)
        self.writetext('longintro...',1)
        introserv = Say('intro')
        #introserv()
        pleasedoserv = Say('please_do')
        self.writetext('starting',1)
        #starts subscriber from activity recognition own
        activity_list = ['brush_hair','chew','clap','drink','eat','jump','pick','pour','sit','smile','stand','talk','walk','wave']
        serv_talk_list = []
        alltests = []

        for activity in activity_list:
            thisserv = Say(activity)
            serv_talk_list.append(thisserv)
        rospy.loginfo('starting experiment')
        # for loop over activities that were selected from a list:
        for activity, say_action in np.random.permutation(zip(activity_list,serv_talk_list)):
            self.writetext(activity,1)
            #say what the person should do (play wav file) and show on the robot screen
            pleasedoserv()
            say_action()
            thistry = Test()
            thistry.activity = activity

            #set up the activity to be recoreded
            #thisActionName = Actname()
            thisActionName_activity = os.path.join(self.testtimedir,'image',"%s.avi"%(activity))
            setname_color_rec(thisActionName_activity)
            if RECORDDEPTH:
                thisActionName_activity = os.path.join(self.testtimedir,'depth',"%s.avi"%(activity))
                setname_depth_rec(thisActionName_activity)

            #starts service from activity recognition, starts recording
            start_color_rec()
            if RECORDDEPTH:
                start_depth_rec()

            start_act()
            #starts 5 seconds timer.
            time.sleep(5)
            #stops recording, activity recognition
            stop_color_rec()
            if RECORDDEPTH:
                stop_depth_rec()
            stop_act()
            with self.mylock:
                thistry.activity_hat = self.actact
                thistry.dic = self.dic
                print(thistry.activity_hat)
                print(self.dic)
            alltests.append(thistry)
        filehandler = open(os.path.join(self.testtimedir,'alltests.obj'),'a')
        pickle.dump(alltests,filehandler)
        filehandler.close()
        #this sucks though. I want a text file like a normal person.
        with open(os.path.join(self.testtimedir,'alltests.txt'),'w') as f:
            for ijkl in alltests:
                f.write("%s %s\n"%(ijkl.activity,ijkl.activity_hat))
        self.writetext('goodbye',1)
        rospy.signal_shutdown('I''m done, so bye! ')

    def writetext(self,text, time_to_display):
        cv2.putText(self.image,text,(350,360),self.font,6,(255,255,255),1)
        try:
            for i in range(0,int(self.r*time_to_display)): ##will display for >>time_to_display<< seconds.
                self.imp.publish(self.bridge.cv2_to_imgmsg(self.image, "bgr8"))
                self.myrate.sleep()
            self.image = deepcopy(self.background)
        except CvBridgeError as e:
            rospy.logerr(e)
        except rospy.ROSException as e:
            rospy.logerr(e)

    def getslatest_activity(self,data):
        with self.mylock:
            self.actact = data

    def getslatest_activityDIC(self,data):
        with self.mylock:
            self.dic = data


    def publish_black(self):
        for i in range(0,10):
            self.imp.publish(self.bridge.cv2_to_imgmsg(self.background, "bgr8"))
            self.myrate.sleep()

    def myhook(self):
        print "shutdown time!"
        #publishing black screen
        if self.imp:
            self.publish_black()
        #rospy.loginfo('stopped everything')
        #for sub in self.subprocesses:
        #    sub.terminate()
        #self.stop_h()

if __name__ == '__main__':
    try:
        rospy.init_node('statemachine_acquire', log_level=rospy.INFO)
        statemachine()
        while not rospy.is_shutdown():
            rospy.spin()
    except rospy.ROSInterruptException:
        pass
