#!/usr/bin/env python

import rospy
import sys
import time
import threading
from std_msgs.msg import UInt16
from sensor_msgs.msg import JointState
from sensor_msgs.msg import CameraInfo

x = 0
y = 0
mylock = threading.Lock()
height = -1
width = -1
myjs = JointState
newdata = False
#
# def set_angles(pan, tilt):
#     time.sleep(0.5)
#
#     js = JointState()
#     js.name = [ "ptu_pan", "ptu_tilt" ]
#     js.velocity = [ 0.3, 0.3 ]
#     js.position = [ pan, tilt ]
#     pub.publish(js)

def get_angles(js):
    mylock.acquire()
    global myjs
    #print(js.name)
    #print(js.velocity)
    #print(js.position)
    myjs = js
    mylock.release()

def mycallbackx(data):
    global x,newdata
    mylock.acquire()
    x = data.data
    newdata = True
    mylock.release()
def mycallbacky(data):
    global y,newdata
    mylock.acquire()
    y = data.data
    newdata= True
    mylock.release()

if __name__ == '__main__':
    #rospy.wait_for_message('/action', UInt16)
    rospy.init_node('headtracking_node')
    print('hello')
    myrate = rospy.Rate(0.6)
    #myjs = rospy.wait_for_message('/joint_states', JointState)
    #get_angles(myjs)
    pub = rospy.Publisher("/ptu/cmd", JointState, queue_size=1)

    jss =  rospy.Subscriber('/joint_states', JointState, get_angles)
    rospy.wait_for_message('/headcenterx', UInt16)
    xs = rospy.Subscriber('/headcenterx', UInt16, mycallbackx)
    ys = rospy.Subscriber('/headcentery', UInt16, mycallbacky)
    camerainfo = rospy.wait_for_message('/camera/rgb/camera_info', CameraInfo)
    print(camerainfo.height)
    print(camerainfo.width)
    global height,width
    height = camerainfo.height
    width = camerainfo.width
    print('did i get here?')
    lowerbound = [width/3,height/3]
    upperbound = [width*2/3,height*2/3]
    myjs_velocity = tuple([ 0.5, 0.5 ])
    while not rospy.is_shutdown():
        #this is now probably a for over names and it will break if the robot has more JointS
        print("Camerainfo is (%d,%d). face detected at %d,%d"%(width,height,x,y))

        mypositions = list(myjs.position)
        for i in range(0,len(myjs.name)):
            if myjs.name[i] == 'ptu_pan':
                if x>upperbound[0]:
                    print("decreasing x")
                    mypositions[i] += -.2
                elif x<lowerbound[0]:
                    print("increasing x")
                    mypositions[i] += .2
                else:
                    print("x unaltered")
            if myjs.name[i] == 'ptu_tilt':
                if y>upperbound[1]:
                    print("decreasing y")
                    mypositions[i] += -.2
                elif y<lowerbound[1]:
                    print("increasing y")
                    mypositions[i] += .2
                else:
                    print("y unaltered")
        myjs.velocity = myjs_velocity
        myjs.position = tuple(mypositions)
        print(myjs)
        mylock.acquire()
        if newdata:
            pub.publish(myjs)
            newdata = False
        mylock.release()

        myrate.sleep();

    #set_angles(           float(sys.argv[1]),            float(sys.argv[2]))
