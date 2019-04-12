#!/usr/bin/env python

import rospy
import sys
import time
import threading
import std_srvs.srv
from std_msgs.msg import UInt16
from sensor_msgs.msg import JointState,  CameraInfo
from face_recognition_ros.msg import HeadsArrayFloat
from copy import deepcopy
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
RESTRICTWITHRATE = True #dangerous to change
TESTING = False
DONTWAITFORGOAL = True # dangerous to change to True

class ControlHead:
    def __init__(self):
        self.mylock = threading.Lock()
        self.myjs = JointState
        self.newdata = False
        #self.anglesstarted = False
        #rospy.wait_for_message('/action', UInt16)
        rospy.init_node('headtracking_node', log_level=rospy.INFO)
        #print('hello')
        ### I should probably check if this is available, then test if it blocks when called and not there, etc.
        self.errorsound = rospy.ServiceProxy('/play_err', std_srvs.srv.Empty)
        theratenum = 10#1.0/0.25
        myrate = rospy.Rate(theratenum)
        #myjs = rospy.wait_for_message('/joint_states', JointState)
        #get_angles(myjs)
        self.pub = rospy.Publisher("/ptu/cmd", JointState, queue_size=1)

        ###we are also initializing lastjs, so we can see if the movement finished or not
        rospy.logwarn('waiting for joint_states topic to publish')
        try:
            self.lastjs =  rospy.wait_for_message('/ptu/joint_states', JointState, timeout= 10)
            rospy.logdebug(self.lastjs)
        except rospy.ROSException as e:
            print(e)
            rospy.logerr(e)
            rospy.signal_shutdown('no heads found within 10 seconds. breaking out')

        jss =  rospy.Subscriber('/ptu/joint_states', JointState, self.get_angles)

        rospy.logwarn('waiting for heads topic to publish')
        try:
            heads =  rospy.wait_for_message('heads', HeadsArrayFloat, timeout= 10)
        except rospy.ROSException as e:
            print(e)
            rospy.logerr(e)
            rospy.signal_shutdown('no heads found within 10 seconds. breaking out')
        hss =  rospy.Subscriber('heads', HeadsArrayFloat, self.updateheads)

        #while not self.anglesstarted:
            ##maybe I need a lock?
        camerainfo = rospy.wait_for_message('/camera/rgb/camera_info', CameraInfo)
        rospy.logdebug(camerainfo.height)
        rospy.logdebug(camerainfo.width)

        self.height = camerainfo.height
        self.width = camerainfo.width
        #print('did i get here?')
        self.setpoint = [self.width/2.0, self.height/3.0]
        nocontrolzonex = 0.133333333333
        nocontrolzoney = 0.133333333333
        self.lowerbound = [self.setpoint[0] - self.width/2*nocontrolzonex, self.setpoint[1] - self.height/2*nocontrolzonex]
        self.upperbound = [self.setpoint[0] + self.width/2*nocontrolzoney, self.setpoint[1] + self.height/2*nocontrolzoney]
        rospy.loginfo('\nlowerbound {},{}\nupperbound {},{}\nsetpoint {},{}'.format(self.lowerbound[0], self.lowerbound[1], self.upperbound[0],self.upperbound[1], self.setpoint[0], self.setpoint[1]))
        #rospy.signal_shutdown('just checking constants')

        self.myjs_max_velocity = tuple([ 0.9, 0.9 ])
        increase_in_angle_of_ptu_pan_to_get_from_middle_to_extreme_right = min([1.2/theratenum, 0.5]) ### needs to be measured. changing the rate changes this!
        increase_in_angle_of_ptu_tilt_to_get_from_middle_to_extreme_bottom = min([0.8/theratenum, 0.5]) ### needs to be measured
        self.kx = increase_in_angle_of_ptu_pan_to_get_from_middle_to_extreme_right/(self.width/2)
        self.ky = increase_in_angle_of_ptu_tilt_to_get_from_middle_to_extreme_bottom/(self.height/2)
        self.kvx = 0.005
        self.kvy = 0.005
        print("kx::: {}".format(self.kx))
        print("ky::: {}".format(self.ky))
        print("kvx::: {}".format(self.kvx))
        print("kvy::: {}".format(self.kvy))

        #### maybe i could get joints tired, that is, if the move too much too fast, they trigger a tired state
        #### where they warn and stop moving.
        self.HA = []
        while not rospy.is_shutdown():
            #this is now probably a for over names and it will break if the robot has more JointS
            if RESTRICTWITHRATE:
                self.docontrol()
            myrate.sleep();




    def get_angles(self, js):
        #self.mylock.acquire()
        #print(js.name)
        #print(js.velocity)
        #print(js.position)
        #rospy.logwarn('gotangles')
        ###maybe this should be a service? I don't want old angles, but I also don't want them updated 9600 times a second.
        self.myjs = js
        #self.anglesstarted = True
        #self.mylock.release()

    def updateheads(self, data):
        with self.mylock:
            self.HA = data.heads
        rospy.logdebug('gotheads')
        if not RESTRICTWITHRATE:
            self.docontrol()
        #print('gotheads')

    def docontrol(self):
        if self.HA:
            rospy.logdebug('haveheads. entering control')
            if len(self.HA)>1:
                rospy.logwarn('Found {} heads. This doesn''t work that well yet! Will track first one'.format(len(self.HA)))
            #length is not zero, right?
            self.x = (self.HA[0].left+self.HA[0].right)/2
            self.y = (self.HA[0].top+self.HA[0].bottom)/2
            #calculate the error for the controller
            deltax = self.x - self.setpoint[0]
            deltay = self.y - self.setpoint[1]
            rospy.logdebug("Camerainfo is (%d,%d). face detected at %f,%f"%(self.width,self.height,self.x,self.y))
            rospy.logdebug("deltax {}, deltay {}".format(deltax,deltay))
            self.changex = -self.kx*deltax
            self.changey = -self.ky*deltay
            self.velx = abs(self.kvx*deltax)
            self.vely = abs(self.kvy*deltay)
            rospy.logdebug("change {}, {}".format(self.changex, self.changey))
            rospy.logdebug("vel {}, {}".format(self.velx, self.vely))
            try:
                mypositions = []
                myvelocities = []
                velocities = tuple([0,0])
                self.beforecontroljs = deepcopy(self.myjs)
                for jointName, jointPosition, jointVelocity in zip(self.myjs.name,self.myjs.position, velocities):
                    oldjp =  jointPosition
                    rospy.logdebug('jointName is: {}'.format(jointName))
                    if jointName == 'ptu_pan':
                        rospy.logdebug('doing ptu_pan stuff')
                        rospy.logdebug(jointName + 'lowerbound {}, upperbound {}'.format(self.lowerbound[0], self.upperbound[0]))
                        if self.x>self.upperbound[0]:
                            rospy.logdebug("decreasing x")
                            #jointPosition += -.2
                        elif self.x<self.lowerbound[0]:
                            rospy.logdebug("increasing x")
                            #jointPosition += .2
                        else:
                            rospy.logdebug("x unaltered")
                        if self.x>self.upperbound[0] or self.x<self.lowerbound[0]:
                            rospy.logdebug("controlling!")
                            jointVelocity = min([self.velx,self.myjs_max_velocity[0]])
                            rospy.logwarn("velx {}, used_velx{}".format(self.velx, jointVelocity))
                            jointPosition = oldjp + self.changex
                            ##TODO: do this in a nice way. read joint limits from somewhere, etc.
                            if abs(jointPosition)>2.8:
                                self.errorsound ()
                                rospy.logwarn('controlling to head position would exceed joint limit! NOT SETTING NEW jointPosition!!!')
                                jointPosition = oldjp

                    if jointName == 'ptu_tilt':
                        rospy.logdebug('doing ptu_tilt stuff')
                        rospy.logdebug(jointName + 'lowerbound {}, upperbound {}'.format(self.lowerbound[1], self.upperbound[1]))

                        if self.y>self.upperbound[1]:
                            rospy.logdebug("decreasing y")
                            #jointPosition += -.2
                        elif self.y<self.lowerbound[1]:
                            rospy.logdebug("increasing y")
                            #jointPosition += .2
                        else:
                            rospy.logdebug("y unaltered")
                        if self.y>self.upperbound[1] or self.y<self.lowerbound[1]:
                            rospy.logdebug("controlling!")
                            jointVelocity = min([self.vely,self.myjs_max_velocity[1]])
                            rospy.logwarn("vely {}, used_vely{}".format(self.vely, jointVelocity))
                            jointPosition = oldjp + self.changey
                            ##TODO: do this in a nice way. read joint limits from somewhere, etc.
                            if abs(jointPosition)>0.8:
                                self.errorsound()
                                rospy.logwarn('controlling to head position would exceed joint limit! NOT SETTING NEW jointPosition!!!')
                                jointPosition = oldjp

                    mypositions.append(jointPosition)
                    myvelocities.append(jointVelocity)
                    if abs(oldjp - jointPosition) > 0.01:
                        rospy.logdebug('would move {} from {} to {}'.format(jointName, oldjp, jointPosition))

                self.myjs.velocity = tuple(myvelocities)
                self.myjs.position = tuple(mypositions)

                #rospy.logwarn('!!!! what is happening? not publishing, just testing!')
                #rospy.logwarn(self.myjs.position)
                #rospy.loginfo(self.myjs)
                #### if i haven't finished my previous movement I should not tell it to move again!
                if DONTWAITFORGOAL or all(abs( jointPosition - jointGoal) < 0.05 for jointPosition, jointGoal in zip(self.beforecontroljs.position, self.lastjs.position)):
                    #
                    if TESTING:
                        rospy.logwarn('would publish, but now I am testing!')
                    else:
                        rospy.logdebug('PUBLISHING!')
                        self.pub.publish(self.myjs)
                        self.lastjs = deepcopy(self.myjs)
                else:
                    rospy.logwarn(self.beforecontroljs.position)
                    rospy.logwarn(self.lastjs.position)
                    rospy.logwarn('movement from previous step still happening, or failed. ')

            except rospy.ROSException as e:
                print(e)
                rospy.logerr(e)
                dir(self.myjs.position)
                print(self.myjs.position)
                rospy.signal_shutdown('error while controlling!')
            with self.mylock:
                self.HA = [] # makes sure I don't keep controlling when no new head is published

#set_angles(           float(sys.argv[1]),            float(sys.argv[2]))


if __name__ == '__main__':
    myheadcontroller = ControlHead()
