#!/usr/bin/env python
'''This structure is synchronizes 2 topics that are publishing at different
 times and makes sure that for each time someone publishes, the latest version
  of the other is used and a paired list is created with the same number of
  elements for both. So far we found 2 uses of this: one is to create a confusion
  matrix, the other is to create a training dataset to train a NN or equivalent
  This is the basic part, which should be subclassed to account for the
   differences in usage of both.

The structure is awkward because of some limitations when plotting things. I am
pretty sure it didn't really solve the problem, but it is 'working', so I am
reluctant to change it.

y       real data or labels or targets
y_hat   feature data or label estimation
    '''
# instantiates listeners for y and y_hat.
# get latest values, creates list and with a service call, calculates the cf or trains

import os
import rospy
import time
try:
    import cPickle as pickle
except:
    import pickle

from std_msgs.msg import String
import std_srvs.srv

def gettype(message_type_str):
    ### thanks to stackexchange and python docs:
    assert type(message_type_str) == type('')
    sep = '.'
    aa = message_type_str.split(sep)
    package = sep.join(aa[0:-1])
    name = aa[-1]
    rospy.logwarn("Custom variable import!!")
    rospy.logwarn("trying to load %s from package: %s"%(name,package))
    mytype = getattr(__import__(package, fromlist=[name]),name)
    return mytype

class Gatherer(object):
    def __init__(self, y_type=String, yhat_type=String):
        self.gfile = os.path.expanduser(rospy.get_param('~glistfile','~/my_gatherer_file'))
        self.synch_appending = rospy.get_param('~synch_appending',False)
        # self.classes = eval(rospy.get_param('~classes','["something","something_else"]'))
        self.classes = rospy.get_param('~classes',["something","something_else"])

        rospy.loginfo('Gatherer initialized')
        assert type(self.classes) == list
        rate_value = rospy.get_param('~rate',5)
        self.rate = rospy.Rate(rate_value)
        self.yhs = rospy.Subscriber('y_hat_topic', yhat_type, self.callback_yhat_update)
        self.ys = rospy.Subscriber('y_topic', y_type, self.callback_y_update)
        self.ds = rospy.Subscriber('done_topic', String, self.callback_done)
        self.sg = rospy.Service('save_gt', std_srvs.srv.Empty,self.savegt)
        self.ssg = rospy.Service('show_gt', std_srvs.srv.Empty,self.showgt)

        self.namespace = rospy.get_param('~namespace','')
        self.dopickle = True
        self.saveastxt = True

        self.ylist = []
        self.yhatlist = []
        self.curry = None
        self.curry_hat = None
        self.lastdata = 0
        #### registers a service to calculate the confusion matrix of what it has so far?
        if self.dopickle:
            rospy.loginfo('dopickle set to true. save_gt service will save a .obj file! ')
        if self.saveastxt:
            rospy.loginfo('saveastxt set to true. save_gt service will save 2 .txt files! ')

    def __del__(self):
        self.yhs.unregister()
        self.ys.unregister()
        self.ds.unregister()
        self.ssg.shutdown('gatherer object deleted by service call')
        self.sg.shutdown('gatherer object deleted by service call')
        rospy.loginfo('Gatherer finished deleting itself!')
        #   rospy.spin()
    def callback_done(self, data):
        #print(data.data)
        if data.data == '1' and self.lastdata == '1':
            #self.calccf(None)
            rospy.logwarn_throttle(60, 'I''m done. Should print output once and then either exit or clear gatherer(?)')
        self.lastdata = data.data
    def callback_y_update(self, data):
        rospy.logdebug(rospy.get_caller_id() + ": I heard %s from y_topic", data.data )
        self.curry = data.data
    def callback_yhat_update(self, data):
        rospy.logdebug(rospy.get_caller_id() + ": I heard %s from y_hat_topic", data.data )
        self.curry_hat = data.data
        if self.synch_appending:
            self.append_y_yhat()
    def append_y_yhat(self):
        ## makes sure that they are the same length, even if they are published at different time intervals
        rospy.logdebug(rospy.get_caller_id() + ": I am pushing into lists: %s ; %s", self.curry,self.curry_hat )
        self.ylist.append(self.curry)
        self.yhatlist.append(self.curry_hat)

    def showgt(self,req):
        print(self.ylist[-1])
        print(self.yhatlist[-1])
        return []
    def savegt(self,req):
        #save for posterity
        thistime = str(time.time())
        if self.saveastxt:
            yfilename    = self.gfile+'_y'      +thistime+'.txt'
            yhatfilename = self.gfile+'_yhat'   +thistime+'.txt'
            rospy.loginfo('saving data as text files \ny: %s and \ny_hat: %s'%(yfilename,yhatfilename))
            with open(yfilename,'w') as f:
                for i in range(0,len(self.ylist)):
                    f.write("%s\n" %str(self.ylist[i])) ### this will maybe mangle data quite a lot. and use a ton of space. maybe I should pickle it?
            with open(yhatfilename,'w') as f:
                for i in range(0,len(self.yhatlist)):
                    f.write("%s\n" %str(self.yhatlist[i])) ### this will maybe mangle data quite a lot.
        if self.dopickle:
            filename    = self.gfile+'_y_yhat'      +thistime+'.obj'
            rospy.loginfo('saving data as obj file \ny and y_hat: %s'%(filename))
            with open(filename,'w') as f:
                pickle.dump(self.ylist,f)
                pickle.dump(self.yhatlist,f)
        if not self.dopickle and not self.saveastxt:
            rospy.logwarn('neither dopickle or saveastxt are set. not doing anything!!!')
        return []

class Gatherer_wrap(object):
    def __init__(self,name):
        print('initializing Gatherer %s'%name)
        rospy.init_node(name, anonymous=True, log_level=rospy.INFO)
        # rospy.init_node(name, anonymous=True, log_level=rospy.DEBUG)

        self.name = name
        self.initsrv = rospy.Service('init_%s'%self.name, std_srvs.srv.Empty,self.initgt)
        self.delsrv = rospy.Service('del_%s'%self.name, std_srvs.srv.Empty,self.cleargt)
        self.mygatherer = None
        #instead of this,,, what about
        if 0:
            self.y_type = y_type
            self.yhat_type = yhat_type
        else: #this:
            y_type_str = rospy.get_param('~y_type')
            yhat_type_str = rospy.get_param('~yhat_type')

            y_type = gettype(y_type_str)
            yhat_type = gettype(yhat_type_str)

            self.y_type = y_type
            self.yhat_type = yhat_type

    def initgt(self,req):
        if self.mygatherer:
            rospy.logwarn(dir(self.mygatherer))
            rospy.logwarn(type(self.mygatherer))
            rospy.logwarn('%s already initialized. will start new instance, but results may not be accurate!'%self.name)
        self.pgtinit()
        rospy.loginfo('new Gatherer instantiated')
        return []

    def pgtinit(self):
        '''this needs to be changed for cfer and trainer'''
        self.mygatherer = Gatherer(y_type=self.y_type,yhat_type=self.yhat_type)
        #assert self.mygatherer.cnf_matrix is None

    def cleargt(self,req):
        #del(self.mygatherer)
        self.mygatherer.__del__() ### delete, delete delete!!!
        self.mygatherer = None
        assert self.mygatherer is None
        rospy.loginfo('Gatherer deleted and set to None')
        return []

if __name__ == '__main__':
    try:
        gwrap = Gatherer_wrap('gatherer')
        r= rospy.Rate(10)

        while not rospy.is_shutdown():
            if not gwrap.mygatherer:
                r.sleep()
            else:
                if not gwrap.mygatherer.synch_appending:
                    gwrap.mygatherer.append_y_yhat()
                gwrap.mygatherer.rate.sleep()

    except rospy.ROSInterruptException:
        pass
