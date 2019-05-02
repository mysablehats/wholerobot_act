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

from std_msgs.msg import String
import std_srvs.srv

from gatherer import Gatherer, Gatherer_wrap

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

class CfGatherer(Gatherer):
    def __init__(self):
        super(CFGatherer,self).__init__(y_type=String,yhat_type=String) ###somthing like this.
        self.ss = rospy.Service('show_cf', std_srvs.srv.Empty,self.calccf)
        self.ssp = rospy.ServiceProxy('_show_gatherer', std_srvs.srv.Empty)
        self.cnf_matrix = None

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
        super(CFGatherer,self).__del__() ###


class CfGatherer_wrap(Gatherer_wrap):
    def __init__(self,name):
        super(CfGatherer_wrap,self).__init__(y_type=String,yhat_type=String)
        self.showsrv = rospy.Service('_show_%s'%self.name, std_srvs.srv.Empty,self.showcf)
        self.blocksrv = rospy.Service('block', std_srvs.srv.Empty,self.block)

    def block(self,req):
        ###blocking call from matplotlib.
        ###this does not work. matplotlib can't thread...
        plt.show()
        return []

    def pgtinit(self):
        '''overrrinding inital gatherer init definition. hopefully.'''
        self.mygatherer = CfGatherer(y_type=self.y_type,yhat_type=self.yhat_type)
        assert self.mygatherer.cnf_matrix is None


    def showcf(self,req):
            if self.mygatherer:
                assert self.mygatherer is not None
                if self.mygatherer.cnf_matrix is not None:
                    rospy.loginfo('Cfn_matrix ready and prepared to be displayed')
                    np.set_printoptions(precision=2)
                    # Plot non-normalized confusion matrix
                    plt.figure("Fig: "+self.mygatherer.namespace)

                    plot_confusion_matrix(self.mygatherer.cnf_matrix, classes=self.mygatherer.classes, title='Confusion matrix, without normalization')
                    # Plot normalized confusion matrix
                    #plt.figure()
                    #plot_confusion_matrix(cnf_matrix, classes=self.classes, normalize=True,
                    #                      title='Normalized confusion matrix')

                    #plt.show(block = False)
                    plt.show()
                    plt.pause(0.001)
                    self.mygatherer.cnf_matrix = None
                    rospy.loginfo('Cfn_matrix ready and prepared to be displayed')
                    return []

if __name__ == '__main__':
    try:
        cferwrap = CfGatherer_wrap('cfer')
        r= rospy.Rate(10)

        while not rospy.is_shutdown():
            if not cferwrap.mygatherer:
                r.sleep()
            else:
                if not cferwrap.mygatherer.synch_appending:
                    cferwrap.mygatherer.append_y_yhat()
                cferwrap.mygatherer.rate.sleep()

    except rospy.ROSInterruptException:
        pass
