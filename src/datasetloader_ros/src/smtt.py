#!/usr/bin/env python
import rospy
import time
import subprocess

from std_srvs.srv import Empty
from std_msgs.msg import String
#from std_msgs.msg import String, Float32MultiArray, MultiArrayDimension
#import os
import caffe_tsn_ros.srv
from datasetloader_ros.srv import *
from gatherer import gettype

class OutStreamWrapper():
    def __init__(self, datasetname, yhat_type, y_type):
        self.init_toter_h_list = []
        self.showv_toter_h_list = []
        self.save_toter_h_list = []
        self.del_toter_h_list = []
        self.subprocesses = []
        self.yhat_type = yhat_type
        self.y_type = y_type
        self.datasetname = datasetname
    def add_outstream(self,outstream,tot,i,output):
        launchername = "ttc_ns.launch.xml"

        if tot == 'cf' or tot == 'test':
            innertotsetting = 'test'
        elif tot == 'train':
            innertotsetting = tot
        else:
            innertotsetting = tot
            rospy.logwarn('tot is ''%s''. neither ''test'' ''cf'' or ''train''. I will probably crash!'%tot)

        thissubprocess = subprocess.Popen(["roslaunch","datasetloader_ros",launchername,
        "node_type:=%s"%(tot),
        "innertotsetting:=%s"%innertotsetting,
        "namespace:=/{}/split_{}".format(outstream,i),
        "filenamesux:={}_{}_split_{}".format(output,outstream,i),
        "dataset:={}".format(self.datasetname),
        "y_type:={}".format(self.y_type), ### premature optimization...
        "yhat_type:={}".format(self.yhat_type),
        "y_hat_input:=/{}/{}".format(outstream,output)])
        self.subprocesses.append(thissubprocess)
        init_toter_h = rospy.ServiceProxy('/{}/split_{}/init_{}er'.format(outstream,i,tot), Empty)
        ### this is hacky. theoretically there should be another service here!
        if tot == 'cf':
            showv_toter_h = rospy.ServiceProxy('/{}/split_{}/show_cf'.format(outstream,i), Empty)
        else:
            showv_toter_h = rospy.ServiceProxy('/{}/split_{}/show_gt'.format(outstream,i), Empty)
        save_toter_h = rospy.ServiceProxy('/{}/split_{}/save_gt'.format(outstream,i), Empty)
        del_toter_h = rospy.ServiceProxy('/{}/split_{}/del_{}er'.format(outstream,i,tot), Empty)
        rospy.wait_for_service('/{}/split_{}/init_{}er'.format(outstream,i,tot))
        self.init_toter_h_list.append(init_toter_h)
        self.showv_toter_h_list.append(showv_toter_h)
        self.save_toter_h_list.append(save_toter_h)
        self.del_toter_h_list.append(del_toter_h)
        return thissubprocess

    def initt(self):
        for inits in self.init_toter_h_list:
            inits()
    def showv(self):
        for inits in self.showv_toter_h_list:
            inits()
    def save(self):
        for inits in self.save_toter_h_list:
            inits()
    def delt(self):
        for inits in self.del_toter_h_list:
            inits()

    def close(self):
        for inits in self.init_toter_h_list:
            inits.close()
        # for inits in self.showv_toter_h_list:
        #     inits()
        for inits in self.save_toter_h_list:
            inits.close()
        for inits in self.del_toter_h_list:
            inits.close()
        ## im not relying in myhook now. it would take some thinking to make it add hooks under this new structure, so i need to kill this thing here at least!

        for sub in self.subprocesses:
            rospy.loginfo('stop a subprocess    ')
            sub.terminate()

class statemachine():
    def __init__(self,tot):
        ### things are launched
        #now I need to send a service call to load split 1
        rospy.loginfo('started')
        ### decides what results we will log
        # if tot == 'train' or tot == 'test':
        #     # self.output = 'scores'
        #     self.iscf = False
        # elif tot == 'cf':
        #     # self.output = 'action'
        #     self.iscf = True
        self.output = rospy.get_param('~output','undefined')
        assert self.output is not 'undefined'
        rospy.loginfo('output set to %s'%self.output)
        self.yhat_type_str = rospy.get_param('~yhat_type')
        self.yhat_type = gettype(self.yhat_type_str)
        self.y_type_str = rospy.get_param('~y_type')
        self.y_type = gettype(self.y_type_str)
        self.done = False
        rospy.wait_for_service('/readpathnode/read_split')
        rospy.loginfo('service read_split okay')
        rospy.wait_for_service('/videofiles/videofiles_stream/play')
        rospy.loginfo('service videofiles_stream/play okay')
        rospy.Subscriber("/readpathnode/done", String, self.donecallback)
        try:
            self.datasetname = rospy.get_param("~dataset")
            ### we don't want the safe version we want to test if we did a good job here. dataset should be kind of global, right? I mean, we aren't training multiple datasets at the same time...
            # self.datasetname = rospy.get_param("dataset","hmdb51")
        except:
            rospy.logwarn('dataset name not set in launch files! using default hmdb51!!')
            self.datasetname = "hmdb51"
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
            flowname = rospy.resolve_name('/flow/%s'%self.output)
            rgbname = rospy.resolve_name('/rgb/%s'%self.output)
            rospy.loginfo('waiting for tsn_caffe to be alive: expecting responses from %s,%s'%(rgbname,flowname))

            ### i could do a custom import here, OR load all the modules I might use and then select them here with a parameter??

            # if self.iscf:
            #     rospy.wait_for_message(flowname, String)
            #     rospy.wait_for_message(rgbname, String)
            # else:
            #     rospy.wait_for_message(flowname, Float32MultiArray)
            #     rospy.wait_for_message(rgbname, Float32MultiArray)
            rospy.wait_for_message(flowname, self.yhat_type)
            rospy.wait_for_message(rgbname, self.yhat_type)

            flowr = rospy.ServiceProxy('/flow/reconf_split', caffe_tsn_ros.srv.split)
            rgbr = rospy.ServiceProxy('/rgb/reconf_split', caffe_tsn_ros.srv.split)

            rospy.loginfo('tsn_caffe is alive. restarting')
            self.stop_h()
            rospy.loginfo('stopped playing. entering loop')

            for i in range(1,4):
                rospy.loginfo('choosing '+str(i) +' split')
                flowr(i)
                rgbr(i)
                rospy.loginfo('reloaded splits!')
                ##we need to reload the split from the classifier as well
                ###arg....
                thisOutStreamWrapper = OutStreamWrapper(self.datasetname,
                                                        self.yhat_type_str,
                                                        self.y_type_str)#,self.iscf)
                for rof in ['rgb','flow']:
                    rospy.loginfo('choosing '+rof +' services and adding them')

                    self.subprocesses.append(thisOutStreamWrapper.add_outstream(rof,tot,i,self.output))

                self.s_h(i)
                time.sleep(3)
                rospy.loginfo('initializing %ser'%tot)
                thisOutStreamWrapper.initt()
                rospy.loginfo('playing until done')
                self.play_h()
                while not self.done:
                    time.sleep(1)
                    try:
                        # if not self.iscf:
                        if not tot == 'cf':
                            thisOutStreamWrapper.showv()
                        # else:
                        #     pass
                        #     #print('not showing output because it is a cfer instance. i''m still working though.')
                    except:
                        print('could not show. wonder why')
                if self.done:
                    rospy.loginfo('showing gathered data')
                    #show_toter_h()
                    #if self.iscf:
                    if tot == 'cf':
                        thisOutStreamWrapper.showv() ### I highjacked this service,, theore
                    else:
                        pass
                    thisOutStreamWrapper.save()
                    thisOutStreamWrapper.delt()
                    self.done = False
                    # init_toter_h.close()
                    # #show_toter_h.close()
                    # save_toter_h.close()
                    # del_toter_h.close()
                    thisOutStreamWrapper.close()
                    ## maybe get a handle for the popen and do a popen.kill()/popen.terminate() ?

            ###after everything finishes, block them plots!
            rospy.signal_shutdown('I''m done, so bye! ')
            # for i in range(1,5):
            #     block_toter_h = rospy.ServiceProxy('/split_{}/block'.format(i), Empty)
            #     #block_toter_h() ##main thread is not in main loop error...

        except rospy.ServiceException, e:
            print "service failed: %s"%e

    def myhook(self):
        print "shutdown time!"
        rospy.loginfo('stopped everything')
        for sub in self.subprocesses:
            try:
                sub.terminate()
            except:
                print('maybe the process was already killed (hopefully!)')
        self.stop_h()

    def donecallback(self,data):
        if data.data == "1":
            self.done = True
            rospy.loginfo('received done signal from readpathnode. will stop playback')
            self.stop_h()
        pass

if __name__ == '__main__':
    try:
        rospy.init_node('totstatemachine_node', log_level=rospy.INFO)
        statemachine('train')
        while not rospy.is_shutdown():
            rospy.spin()
    except rospy.ROSInterruptException as e:

        print(e)
