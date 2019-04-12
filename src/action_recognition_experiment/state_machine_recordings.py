#!/usr/bin/env python
import rospy
import time
from datasetloader_ros.srv import *
from std_srvs.srv import Empty
from std_msgs.msg import String
#import os
import subprocess

class statemachine():
    def __init__(self):
        ### things are launched
        #now I need to send a service call to load split 1
        self.done = False
        rospy.wait_for_service('/readpathnode/read_split')
        rospy.wait_for_service('/videofiles/videofiles_stream/play')
        rospy.Subscriber("/readpathnode/done", String, self.donecallback)
        rospy.on_shutdown(self.myhook)
        try:
            self.s_h = rospy.ServiceProxy('/readpathnode/read_split', split)
            self.play_h = rospy.ServiceProxy('/videofiles/videofiles_stream/play', Empty)
            self.stop_h = rospy.ServiceProxy('/videofiles/videofiles_stream/stop', Empty)
            # os.system("roslaunch datasetloader_ros cfer_ns.launch namespace:=split_setup")
            # os.system("roslaunch datasetloader_ros cfer_ns.launch namespace:=split_1")
            # os.system("roslaunch datasetloader_ros cfer_ns.launch namespace:=split_2")
            # os.system("roslaunch datasetloader_ros cfer_ns.launch namespace:=split_3")
            # os.system("roslaunch datasetloader_ros cfer_ns.launch namespace:=split_4")

            # subprocess.Popen(["roslaunch","datasetloader_ros","cfer_ns.launch","namespace:=split_2"])
            # subprocess.Popen(["roslaunch","datasetloader_ros","cfer_ns.launch","namespace:=split_3"])
            # subprocess.Popen(["roslaunch","datasetloader_ros","cfer_ns.launch","namespace:=split_4"])

            self.subprocesses = []
            self.stop_h()
            rospy.loginfo('stopped everything')
            time.sleep(1)
            rospy.loginfo('choosing 1 split')
            self.s_h(1)
            time.sleep(3)
            rospy.loginfo('playing')
            self.play_h()
            rospy.loginfo('waiting for tsn_caffe to be alive')
            rospy.wait_for_message('/action', String)
            rospy.loginfo('tsn_caffe is alive. restarting')
            self.stop_h()
            for i in range(1,5):
                rospy.loginfo('choosing '+str(i) +' split')
                thissubprocess = subprocess.Popen(["roslaunch","datasetloader_ros","cfer_ns.launch","namespace:=split_{}".format(i)])
                self.subprocesses.append(thissubprocess)
                init_cfer_h = rospy.ServiceProxy('/split_{}/init_cfer'.format(i), Empty)
                show_cfer_h = rospy.ServiceProxy('/split_{}/show_cf'.format(i), Empty)
                del_cfer_h = rospy.ServiceProxy('/split_{}/del_cfer'.format(i), Empty)
                rospy.wait_for_service('/split_{}/init_cfer'.format(i))
                self.s_h(i)
                time.sleep(3)
                rospy.loginfo('initialing cfer')
                init_cfer_h()
                rospy.loginfo('playing until done')
                self.play_h()
                while not self.done:
                    time.sleep(1)
                if self.done:
                    rospy.loginfo('showing cf')
                    show_cfer_h()
                    del_cfer_h ()
                    self.done = False
                    init_cfer_h.close()
                    show_cfer_h.close()
                    del_cfer_h.close()
                    ## maybe get a handle for the popen and do a popen.kill()/popen.terminate() ?

            ###after everything finishes, block them plots!
            rospy.signal_shutdown('I''m done, so bye! ')
            for i in range(1,5):
                block_cfer_h = rospy.ServiceProxy('/split_{}/block'.format(i), Empty)
                #block_cfer_h() ##main thread is not in main loop error...

        except rospy.ServiceException, e:
            print "service failed: %s"%e

    def myhook(self):
        print "shutdown time!"
        rospy.loginfo('stopped everything')
        for sub in self.subprocesses:
            sub.terminate()
        self.stop_h()

    def donecallback(self,data):
        if data.data == "1":
            self.done = True
            rospy.loginfo('received done signal from readpathnode. will stop playback')
            self.stop_h()
        pass

if __name__ == '__main__':
    try:
        rospy.init_node('mystatemachine_node', log_level=rospy.INFO)
        statemachine()
        while not rospy.is_shutdown():
            rospy.spin()
    except rospy.ROSInterruptException:
        pass
