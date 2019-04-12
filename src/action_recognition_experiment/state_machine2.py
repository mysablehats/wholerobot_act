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
from caffe_tsn_ros.msg import ActionDic, Action
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

class ClassifierContainer():
    def __init__(self):
        self.classifiers = []
        self.alltests = []
    def pushback(self, classc):
        thisClassifierControl = ClassifierControl(classc)
        self.classifiers.append(thisClassifierControl)
    def start_act(self):
        for aCC in self.classifiers:
            aCC.start_act()
    def stop_act(self):
        for aCC in self.classifiers:
            aCC.stop_act()
    def gather_res(self,activity):
        ### if we have N classifiers running,
        ### for each test executed will append N versions of thistry

        for aCC in self.classifiers:
            thistry = Test()
            thistry.activity = activity
            thistry.activity_hat = aCC.actact
            thistry.dic = aCC.dic
            thistry.name = aCC.name
            print(thistry.activity_hat)
            print(thistry.dic)
            print(thistry.name)
            self.alltests.append(deepcopy(thistry))

class ClassifierControl():
    def __init__(self, name):
        #check if activity recognition node is alive
        self.name = name
        if 'rgb' in name:
            self.type_class = 'rgb'
        if 'flow' in name:
            self.type_class = 'flow'

        while not '/%s/class_tsn_%s/alive'%(name,self.type_class) in rosparam.list_params('/'): # the naming here is dumb..
            rospy.logwarn('classifier not started. waiting 3 seconds for it to start')
            time.sleep(3)
        while rosparam.get_param('/%s/class_tsn_%s/alive'%(name,self.type_class)) is not 1:
            rospy.loginfo('classifier started, but not alive. waiting 1 second for it to start')
            time.sleep(1)

        self.start_act = rospy.ServiceProxy('/%s/start_vidscores'%(name), Empty)
        self.stop_act  = rospy.ServiceProxy('/%s/stop_vidscores'%(name) , Empty)
        rospy.Subscriber('/%s/action_own_label'%(name)    ,Action   ,self.getslatest_activity   ,queue_size=1)
        rospy.Subscriber('/%s/action_own_label_dic'%(name),ActionDic,self.getslatest_activityDIC,queue_size=1)
        self.actact = []
        self.dic = []

    def getslatest_activity(self,data):
        self.actact = data

    def getslatest_activityDIC(self,data):
        self.dic = data

class Show():
    def __init__(self):
        self.imp = rospy.Publisher('/screen',Image, queue_size=1)
        self.bridge = CvBridge()
        self.font = cv2.FONT_HERSHEY_SIMPLEX
        self.background = np.zeros((720,1440,3),np.uint8)
        self.image = deepcopy(self.background)
        self.r = 30
        self.myrate = rospy.Rate(self.r)
        rospy.on_shutdown(self.myhook)

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


class statemachine():
    def __init__(self):
        rospy.on_shutdown(self.myhook)
        global DOSAY
        try:
            rospy.wait_for_service('play/intro',timeout=1)
            DOSAY = True
        except:
            rospy.logwarn('bad_speech services do not seem to be running. will work without voice!')

        self.myCC = ClassifierContainer()
        self.myCC.pushback('rgb1')
        self.myCC.pushback('flow1')
        rospy.loginfo('tsn_caffe is alive. starting')
        self.start_color_rec   = rospy.ServiceProxy('/rec_color/rec'     , Empty)
        self.stop_color_rec    = rospy.ServiceProxy('/rec_color/stop'    , Empty)
        self.setname_color_rec = rospy.ServiceProxy('/rec_color/set_name', Actname)

        usewebcam = False
        try:
            self.RECORDDEPTH = rospy.get_param('~record_depth')
        except:
            self.RECORDDEPTH = False
            for listy in rospy.get_published_topics():
                for items in listy:
                     if 'depth' in items:
                         self.RECORDDEPTH = True
                         self.start_depth_rec   = rospy.ServiceProxy('/rec_depth/rec'     , Empty)
                         self.stop_depth_rec    = rospy.ServiceProxy('/rec_depth/stop'    , Empty)
                         self.setname_depth_rec = rospy.ServiceProxy('/rec_depth/set_name', Actname)

                     if 'webcam' in items:
                         usewebcam = True
        if usewebcam:
            rospy.logwarn('you seem to be using a webcam. will not try to record DEPTH')

        if not self.RECORDDEPTH and not usewebcam:
            rospy.logerr('don''t know what your input is' )

        testdir = "/mnt/externaldrive/var/datasets/test/"
        fps = 30
        self.testtimedir = testdir+time.strftime("%Y%m%d-%H%M%S",time.gmtime())
        os.mkdir(self.testtimedir)
        try:
            os.remove(os.path.join(testdir,'latest'))
        except:
            pass
        os.symlink(self.testtimedir,os.path.join(testdir,'latest'))
        os.mkdir(os.path.join(self.testtimedir,'depth'))
        os.mkdir(os.path.join(self.testtimedir,'image'))

        myShow = Show()
        #while not rospy.is_shutdown():
        myShow.writetext('Hello World',1)
        helloserv = Say('hello_world')
        helloserv()

        #    a.sleep()
        time.sleep(3)
        myShow.writetext('longintro...',1)
        introserv = Say('intro')
        introserv()
        pleasedoserv = Say('please_do')
        myShow.writetext('starting',1)
        #starts subscriber from activity recognition own
        activity_list = ['brush_hair','chew','clap','drink','eat','jump','pick','pour','sit','smile','stand','talk','walk','wave']
        serv_talk_list = []

        for activity in activity_list:
            thisserv = Say(activity)
            serv_talk_list.append(thisserv)
        rospy.loginfo('starting experiment')
        # for loop over activities that were selected from a list:
        for activity, say_action in np.random.permutation(zip(activity_list,serv_talk_list)):
            myShow.writetext(activity,1)
            #say what the person should do (play wav file) and show on the robot screen
            pleasedoserv()
            say_action()

            #set up the activity to be recorded
            thisActionName_activity = os.path.join(self.testtimedir,'image',"%s.avi"%(activity))
            self.setname_color_rec(thisActionName_activity)
            if self.RECORDDEPTH:
                thisActionName_activity = os.path.join(self.testtimedir,'depth',"%s.avi"%(activity))
                self.setname_depth_rec(thisActionName_activity)

            #starts recording
            self.start_color_rec()
            if self.RECORDDEPTH:
                self.start_depth_rec()
            #starts services from activity recognition classifiers
            self.myCC.start_act()
            #starts 5 seconds timer.
            time.sleep(5)
            #stops recording, activity recognition
            self.stop_color_rec()
            if self.RECORDDEPTH:
                self.stop_depth_rec()
            self.myCC.stop_act()
            #gather the results of all classifiers started in the container
            self.myCC.gather_res(activity)
        filehandler = open(os.path.join(self.testtimedir,'alltests.obj'),'a')
        pickle.dump(self.myCC.alltests,filehandler)
        filehandler.close()
        #this sucks though. I want a text file like a normal person.
        with open(os.path.join(self.testtimedir,'alltests.txt'),'w') as f:
            for ijkl in self.myCC.alltests:
                f.write("Target:%s %s: Best estimate: %s Confidence:%f\n"%(ijkl.activity, ijkl.name ,ijkl.activity_hat.action, ijkl.activity_hat.confidence))
        myShow.writetext('goodbye',1)
        rospy.signal_shutdown('I''m done, so bye! ')

    def myhook(self):
        print "shutdown time!"
        ### need to stop all recordings
        try:
            self.stop_color_rec()
            if self.RECORDDEPTH:
                self.stop_depth_rec()
        except rospy.ROSException as e:
            rospy.logerr(e)

        ##and stop the classifiers
        try:
            self.myCC.stop_act()
        except rospy.ROSException as e:
            rospy.logerr(e)


if __name__ == '__main__':
    try:
        rospy.init_node('statemachine_acquire', log_level=rospy.INFO)
        statemachine()
        while not rospy.is_shutdown():
            rospy.spin()
    except rospy.ROSInterruptException:
        pass
