#!/usr/bin/env python

import rospy
import sys
import time
import threading
from std_msgs.msg import UInt16
from sensor_msgs.msg import JointState
from sensor_msgs.msg import CameraInfo
from face_recognition_ros.msg import HeadsArray

#global HA, mylock, height, width, myjs, newdata

#
# def set_angles(pan, tilt):
#     time.sleep(0.5)
#
#     js = JointState()
#     js.name = [ "ptu_pan", "ptu_tilt" ]
#     js.velocity = [ 0.3, 0.3 ]
#     js.position = [ pan, tilt ]
#     pub.publish(js)
class ControlHead:
    def __init__(self):
        self.HA = []
        self.mylock = threading.Lock()
        self.myjs = JointState
        self.newdata = False
        #self.anglesstarted = False
        #rospy.wait_for_message('/action', UInt16)
        rospy.init_node('headtracking_node')
        print('hello')
        myrate = rospy.Rate(1)
        #myjs = rospy.wait_for_message('/joint_states', JointState)
        #get_angles(myjs)
        pub = rospy.Publisher("/ptu/cmd", JointState, queue_size=1)

        ###we are also initializing lastjs, so we can see if the movement finished or not
        rospy.logwarn('waiting for joint_states topic to publish')
        try:
            lastjs =  rospy.wait_for_message('/joint_states', JointState, timeout= 10)
        except rospy.ROSException as e:
            print(e)
            rospy.logerr(e)
            rospy.signal_shutdown('no heads found within 10 seconds. breaking out')

        jss =  rospy.Subscriber('/joint_states', JointState, self.get_angles)

        rospy.logwarn('waiting for heads topic to publish')
        try:
            heads =  rospy.wait_for_message('heads', HeadsArray, timeout= 10)
        except rospy.ROSException as e:
            print(e)
            rospy.logerr(e)
            rospy.signal_shutdown('no heads found within 10 seconds. breaking out')
        hss =  rospy.Subscriber('heads', HeadsArray, self.updateheads)

        #while not self.anglesstarted:
            ##maybe I need a lock?
        camerainfo = rospy.wait_for_message('/camera/rgb/camera_info', CameraInfo)
        print(camerainfo.height)
        print(camerainfo.width)

        height = camerainfo.height
        width = camerainfo.width
        print('did i get here?')
        lowerbound = [width/3,height/3]
        upperbound = [width*2/3,height*2/3]
        myjs_velocity = tuple([ 0.65, 0.65 ])
        increase_in_angle_of_ptu_pan_to_get_from_middle_to_extreme_right = 0.6 ### needs to be measured
        increase_in_angle_of_ptu_tilt_to_get_from_middle_to_extreme_bottom = 0.35 ### needs to be measured
        kx = increase_in_angle_of_ptu_pan_to_get_from_middle_to_extreme_right/(width/2)
        ky = increase_in_angle_of_ptu_tilt_to_get_from_middle_to_extreme_bottom/(height/2)
        print("kx::: {}".format(kx))
        print("ky::: {}".format(ky))
        #### maybe i could get joints tired, that is, if the move too much too fast, they trigger a tired state
        #### where they warn and stop moving.
        while not rospy.is_shutdown():
            #this is now probably a for over names and it will break if the robot has more JointS
            x = 0
            y = 0
            deltax = 0
            deltay = 0
            if self.HA:
                if len(self.HA)>1:
                    rospy.loginfo('Found {} heads. Will track first one'.format(len(HA)))
                #length is not zero, right?
                x = (self.HA[0].left+self.HA[0].right)/2
                y = (self.HA[0].top+self.HA[0].bottom)/2
                #calculate the error for the controller
                deltax = x - width/2
                deltay = y - height/2
                print("Camerainfo is (%d,%d). face detected at %d,%d"%(width,height,x,y))
                print("deltax {}, deltay {}".format(deltax,deltay))
                changex = -kx*deltax
                changey = -ky*deltay
                print("change {}, {}".format(changex, changey))
            try:
                mypositions = []

                if self.HA:
                    #self.mylock.acquire()
                    self.beforecontroljs = self.myjs
                    iterset = zip(self.myjs.name,self.myjs.position)
                    #self.mylock.release()
                    rospy.logwarn('have heads')
                    for jointName, jointPosition in iterset:
                        oldjp =  jointPosition
                        print('jointName is: {}'.format(jointName))
                        if jointName == 'ptu_pan':
                            print('doing ptu_pan stuff')
                            print('lowerbound {}, upperbound {}'.format(lowerbound[0], upperbound[0]))
                            if x>upperbound[0]:
                                print("decreasing x")
                                jointPosition += -.2
                            elif x<lowerbound[0]:
                                print("increasing x")
                                jointPosition += .2
                            else:
                                print("x unaltered")
                            if x>upperbound[0] or x<lowerbound[0]:
                                print("controlling!")

                                jointPosition = oldjp + changex

                        if jointName == 'ptu_tilt':
                            print('doing ptu_tilt stuff')
                            print('lowerbound {}, upperbound {}'.format(lowerbound[1], upperbound[1]))

                            if y>upperbound[1]:
                                print("decreasing y")
                                jointPosition += -.2
                            elif y<lowerbound[1]:
                                print("increasing y")
                                jointPosition += .2
                            else:
                                print("y unaltered")
                            if y>upperbound[1] or y<lowerbound[1]:
                                print("controlling!")

                                jointPosition = oldjp + changey

                        mypositions.append(jointPosition)
                        if abs(oldjp - jointPosition) > 0.01:
                            print('would move {} from {} to {}'.format(jointName, oldjp, jointPosition))

                self.myjs.velocity = myjs_velocity
                self.myjs.position = tuple(mypositions)

                #self.mylock.acquire()
                if self.newdata:
                    rospy.logwarn('!!!! what is happening? not publishing, just testing!')
                    rospy.logwarn(self.myjs.position)
                    rospy.loginfo(self.myjs)
                    #### if i haven't finished my previous movement I should not tell it to move again!
                    if all(abs( jointPosition - jointGoal) < 0.05 for jointPosition, jointGoal in zip(self.beforecontroljs.position, lastjs.position)):
                        pub.publish(self.myjs)
                        lastjs = self.myjs
                    else:
                        rospy.logwarn(self.beforecontroljs.position)
                        rospy.logwarn(lastjs.position)
                        rospy.logwarn('movement from previous step still happening, or failed. ')
                    self.newdata = False
                    self.HA = []
                #self.mylock.release()

            except:
                dir(self.myjs.position)
                print(self.myjs.position)

            myrate.sleep();




    def get_angles(self, js):
        #self.mylock.acquire()
        #print(js.name)
        #print(js.velocity)
        #print(js.position)
        #rospy.logwarn('gotangles')
        self.myjs = js
        #self.anglesstarted = True
        #self.mylock.release()

    def updateheads(self, data):
        #self.mylock.acquire()
        self.HA = data.heads
        self.newdata= True
        print('gotheads')
        rospy.logwarn('gotheads')
        #self.mylock.release()

    #set_angles(           float(sys.argv[1]),            float(sys.argv[2]))


if __name__ == '__main__':
    myheadcontroller = ControlHead()
