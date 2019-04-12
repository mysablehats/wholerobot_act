#!/usr/bin/env python
import rospy
import time
from std_srvs.srv import Empty
import subprocess

DOSAY = False

class Rec():
    def __init__(self, topic, name, fps, duration, dirdir, activity ):

        self.topic = topic
        self.name = name
        self.fps = fps
        self.dir = dirdir
        self.activity = activity
        self.duration = duration
        #self.thisprocess = []
        rospy.Service('~/%s/%s/rec'%(self.name,self.activity), Empty, self.rec)
        #rospy.Service('rec', String, self.rec)

        rospy.Service('~/%s/%s/stop'%(self.name,self.activity), Empty, self.terminate)
    def rec(self,req):
        ###so after the first line we can already break out:
        for nothing in self.prec():
            print(nothing)
            break
        time.sleep(self.duration)
        self.terminate('')
        return []
    def prec(self):
        #activity = data.data
        self.thisprocess = subprocess.Popen(["rosrun","image_view","video_recorder","image:=%s"%self.topic,"_fps:=%d"%self.fps,"_filename:=%s/%s_%s.avi"%(self.dir,self.name,self.activity)],stdout=subprocess.PIPE)
        rospy.loginfo('started recording %s'%self.activity)

        #outD, errD = thisDsubprocess.communicate()
        for stl in iter(self.thisprocess.stdout.readline,""):
            print(stl)
            ##must mean I've started recording.
            yield stl
        self.thisprocess.stdout.close()

    def terminate(self,req):
        self.thisprocess.terminate()
        return []

if __name__ == '__main__':
    try:
        rospy.init_node('recorder_launcher', anonymous=True, log_level=rospy.INFO)
        topic = rospy.get_param('~image')
        name = rospy.get_param('~name', 'image')
        fps = rospy.get_param('~fps',30)
        dirdir = rospy.get_param('~dir')
        duration = rospy.get_param('~duration',5)
        activity = rospy.get_param('~activity')
        Rec( topic, name, fps, duration, dirdir, activity)
        while not rospy.is_shutdown():
            rospy.spin()
    except rospy.ROSInterruptException:
        pass
