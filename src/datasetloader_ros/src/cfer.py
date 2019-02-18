#!/usr/bin/env python

# instantiates listeners for y and y_hat.
# get latest values, creates list and with a service call, calculates the cf

import rospy
import os
from std_msgs.msg import String
import std_srvs.srv

import itertools
import numpy as np
import matplotlib.pyplot as plt

import time
#from sklearn import svm, datasets
#from sklearn.model_selection import train_test_split
from sklearn.metrics import confusion_matrix

def plot_confusion_matrix(cm, classes,
                          normalize=False,
                          title='Confusion matrix',
                          cmap=plt.cm.Blues):
    """
    This function prints and plots the confusion matrix.
    Normalization can be applied by setting `normalize=True`.
    """
    if normalize:
        cm = cm.astype('float') / cm.sum(axis=1)[:, np.newaxis]
        print("Normalized confusion matrix")
    else:
        print('Confusion matrix, without normalization')

    print(cm)
    plt.ion()
    plt.imshow(cm, interpolation='nearest', cmap=cmap)
    plt.title(title)
    plt.colorbar()
    tick_marks = np.arange(len(classes))
    plt.xticks(tick_marks, classes, rotation=45)
    plt.yticks(tick_marks, classes)

    fmt = '.2f' if normalize else 'd'
    thresh = cm.max() / 2.
    for i, j in itertools.product(range(cm.shape[0]), range(cm.shape[1])):
        plt.text(j, i, format(cm[i, j], fmt),
                 horizontalalignment="center",
                 color="white" if cm[i, j] > thresh else "black")

    plt.ylabel('True label')
    plt.xlabel('Predicted label')
    plt.tight_layout()

class Cfer():
    def __init__(self):
        self.cffile = os.path.expanduser(rospy.get_param('~cflistfile','~/myfule.txt'))
        self.y_hat_topic = rospy.get_param('~y_hat_topic','/subject/action')
        self.y_topic = rospy.get_param('~y_topic','/subject/action')
        self.done_topic = rospy.get_param('~done_topic','')
        self.namespace = rospy.get_param('~namespace','')
        self.synch_appending = rospy.get_param('~synch_appending',False)
        self.classes = eval(rospy.get_param('~classes','["something","something_else"]')) ### will get evaluated. this is a possible security issue!
        rospy.loginfo('Cfer initialized')
        self.cnf_matrix = None
        assert type(self.classes) == list
        rate_value = rospy.get_param('~rate',5)
        self.rate = rospy.Rate(rate_value)
        self.yhs = rospy.Subscriber(self.y_hat_topic, String, self.callback_yhat_update)
        self.ys = rospy.Subscriber(self.y_topic, String, self.callback_y_update)
        self.ds = rospy.Subscriber(self.done_topic, String, self.callback_done)
        self.ss = rospy.Service('show_cf', std_srvs.srv.Empty,self.calccf)
        self.ssp = rospy.ServiceProxy('_show_cfer', std_srvs.srv.Empty)
        self.ylist = []
        self.yhatlist = []
        self.curry = None
        self.curry_hat = None
        self.lastdata = 0
        #### registers a service to calculate the confusion matrix of what it has so far?
    def __del__(self):
        self.yhs.unregister()
        self.ys.unregister()
        self.ds.unregister()
        self.ss.shutdown('cfer object deleted by service call')
        self.ssp.close()
        rospy.loginfo('Cfer finished deleting itself!')
        #   rospy.spin()
    def callback_done(self, data):
        #print(data.data)
        if data.data == '1' and self.lastdata == '1':
            #self.calccf(None)
            rospy.logwarn_throttle(60, 'I''m done. Should print cf once and then either exit or clear cf(?)')
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
    def calccf(self, req):
        #first save for posterity
        with open(self.cffile+'_y'+str(time.time())+'.txt','w') as f:
            for i in range(0,len(self.ylist)):
                f.write("%s\n" %self.ylist[i])
        with open(self.cffile+'_yhat'+str(time.time())+'.txt','w') as f:
            for i in range(0,len(self.yhatlist)):
                f.write("%s\n" %self.yhatlist[i])


        ### This maybe is slow, so I need to make sure it is non-blocking
        ### right now does nothing.
        rospy.loginfo('erm, calculate confusion matrix!')
        y_pred = np.array(self.yhatlist)
        y_test = np.array(self.ylist)
        for i in range(0,len(y_test)):
            if y_test[i] == None:
                y_test[i] = "unknown"
            if y_pred[i] == None:
                y_pred[i] = "unknown"
        print("ypred:")
        print(y_pred)
        print("ytest:")
        print(y_test)
        self.cnf_matrix = confusion_matrix(y_test, y_pred, labels=self.classes)
        self.ssp()
        rospy.loginfo('done calculating and showing confusion matrix!')
        return []

class Cfer_wrap():
    def __init__(self):
        rospy.init_node('cfer', anonymous=True)
        self.initsrv = rospy.Service('init_cfer', std_srvs.srv.Empty,self.initcf)
        self.delsrv = rospy.Service('del_cfer', std_srvs.srv.Empty,self.clearcf)
        self.showsrv = rospy.Service('_show_cfer', std_srvs.srv.Empty,self.showcf)
        self.blocksrv = rospy.Service('block', std_srvs.srv.Empty,self.block)
        self.mycfer = None

    def block(self,req):
        ###blocking call from matplotlib.
        ###this does not work. matplotlib can't thread...
        plt.show()
        return []
    def initcf(self,req):
        if self.mycfer:
            rospy.logwarn(dir(self.mycfer))
            rospy.logwarn(type(self.mycfer))
            rospy.logwarn('cfer already initialized. will start new instance, but results may not be accurate!')
        self.mycfer = Cfer()
        assert self.mycfer.cnf_matrix is None
        rospy.loginfo('new Cfer instantiated')
        return []

    def clearcf(self,req):
        #del(self.mycfer)
        self.mycfer.__del__() ### delete, delete delete!!!
        self.mycfer = None
        assert self.mycfer is None
        rospy.loginfo('Cfer deleted and set to None')
        return []

    def showcf(self,req):
            if self.mycfer:
                assert self.mycfer is not None
                if self.mycfer.cnf_matrix is not None:
                    rospy.loginfo('Cfn_matrix ready and prepared to be displayed')
                    np.set_printoptions(precision=2)
                    # Plot non-normalized confusion matrix
                    plt.figure("Fig: "+self.mycfer.namespace)

                    plot_confusion_matrix(self.mycfer.cnf_matrix, classes=self.mycfer.classes, title='Confusion matrix, without normalization')
                    # Plot normalized confusion matrix
                    #plt.figure()
                    #plot_confusion_matrix(cnf_matrix, classes=self.classes, normalize=True,
                    #                      title='Normalized confusion matrix')

                    #plt.show(block = False)
                    plt.show()
                    plt.pause(0.001)
                    self.mycfer.cnf_matrix = None
                    rospy.loginfo('Cfn_matrix ready and prepared to be displayed')
                    return []

if __name__ == '__main__':
    try:
        cferwrap = Cfer_wrap()
        r= rospy.Rate(10)

        while not rospy.is_shutdown():
            if not cferwrap.mycfer:
                r.sleep()
            else:
                if not cferwrap.mycfer.synch_appending:
                    cferwrap.mycfer.append_y_yhat()
                cferwrap.mycfer.rate.sleep()

    except rospy.ROSInterruptException:
        pass
