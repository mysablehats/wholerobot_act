#!/usr/bin/env python

# instantiates listeners for y and y_hat.
# get latest values, creates list and with a service call, calculates the cf

import rospy
import itertools
import numpy as np
import matplotlib.pyplot as plt

#from sklearn import svm, datasets
#from sklearn.model_selection import train_test_split
from sklearn.metrics import confusion_matrix

from std_msgs.msg import String, Float32MultiArray, MultiArrayDimension
import std_srvs.srv

from gatherer import Gatherer, Gatherer_wrap

class TGatherer(Gatherer):
    def __init__(self,**kwargs):
        print('initializing TGatherer')
        self.ss = rospy.Service('show_cf', std_srvs.srv.Empty,self.calccf)
        self.ssp = rospy.ServiceProxy('show_gatherer', std_srvs.srv.Empty)
        self.cnf_matrix = None
        super(TGatherer,self).__init__(**kwargs) ###somthing like this.

    def showgt(self,req):
        ###overrrinding
        print(self.ylist[-1])
        print(len(self.yhatlist[-1]))
        return []

    def calccf(self, req):
        #first save for posterity
        self.savegt([])

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
    def __del__(self):
        self.ssp.close()
        super(TGatherer,self).__del__() ###


class TGatherer_wrap(Gatherer_wrap):
    def __init__(self,name):
        print('initializing TGatherer_wrap')

        super(TGatherer_wrap,self).__init__(name, y_type=String, yhat_type=Float32MultiArray)
        self.showsrv = rospy.Service('show_%s'%self.name, std_srvs.srv.Empty,self.showcf)
        self.blocksrv = rospy.Service('block', std_srvs.srv.Empty,self.block)

    def block(self,req):
        ###blocking call from matplotlib.
        ###this does not work. matplotlib can't thread...
        #plt.show()
        pass
        return []

    def pgtinit(self):
        '''overrrinding inital gatherer init definition. hopefully.'''
        print('overrrinding to TGatherer')
        self.mygatherer = TGatherer(y_type=self.y_type,yhat_type=self.yhat_type)
        #assert self.mygatherer.cnf_matrix is None


    def showcf(self,req):
            if self.mygatherer:
                pass
                # assert self.mygatherer is not None
                # if self.mygatherer.cnf_matrix is not None:
                #     rospy.loginfo('Cfn_matrix ready and prepared to be displayed')
                #     np.set_printoptions(precision=2)
                #     # Plot non-normalized confusion matrix
                #     plt.figure("Fig: "+self.mygatherer.namespace)
                #
                #     plot_confusion_matrix(self.mygatherer.cnf_matrix, classes=self.mygatherer.classes, title='Confusion matrix, without normalization')
                #     # Plot normalized confusion matrix
                #     #plt.figure()
                #     #plot_confusion_matrix(cnf_matrix, classes=self.classes, normalize=True,
                #     #                      title='Normalized confusion matrix')
                #
                #     #plt.show(block = False)
                #     plt.show()
                #     plt.pause(0.001)
                #     self.mygatherer.cnf_matrix = None
                #     rospy.loginfo('Cfn_matrix ready and prepared to be displayed')
                #     return []

if __name__ == '__main__':
    try:
        twrap = TGatherer_wrap('trainer')
        r= rospy.Rate(10)

        while not rospy.is_shutdown():
            if not twrap.mygatherer:
                r.sleep()
            else:
                if not twrap.mygatherer.synch_appending:
                    twrap.mygatherer.append_y_yhat()
                twrap.mygatherer.rate.sleep()

    except rospy.ROSInterruptException:
        pass
