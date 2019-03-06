#!/usr/bin/env python3
#oh name collisions. we are not using PIL though, are we?
#from PIL import Image
import face_recognition
import roslib
roslib.load_manifest('face_recognition_ros')
import sys
import rospy
import cv2
import time
## this should be crashing. i forgot to install this guy
from std_msgs.msg import UInt16
import sensor_msgs
from cv_bridge import CvBridge, CvBridgeError
from face_recognition_ros.msg import Heads,HeadsArray
import numpy as np

####TODO: There is a serialization error when trying to publish images. I thought it was a numpy thing, that it changed the array when I do the .asarray command, but the .dtype continues to be uint8, so I don't think that is it. I think that some other internal variable changed

class find_faces:
  ''' I don't really know how to publish a lot of head centers;
   I can use numpy ros stuff, but then cpp code will have a problem with it;
   I can set a maximum number of heads and instantiate a lot of head1, head2,
   etc stuff'''
  def __init__(self):
    #imout = rospy.get_param('~image_output', "face_overlay_image_raw")
    print('hello')
    rospy.loginfo('log hello')
    #self.image_pub = rospy.Publisher(imout,sensor_msgs.msg.Image, queue_size=1)
    self.heads_pub = rospy.Publisher('heads', HeadsArray, queue_size=1)
    imin = rospy.get_param('~image_input', "videofiles/image_raw")

    self.bridge = CvBridge()
    try:
        rospy.wait_for_message(imin, sensor_msgs.msg.Image, timeout=5)
    except rospy.ROSException as e:
        print(e)
        rospy.logerr(e)
        rospy.signal_shutdown('could not receive images in 5 seconds. check networking settings and topics. shutting down!')

    self.image_sub = rospy.Subscriber(imin,sensor_msgs.msg.Image,self.callback)

    self.headcenterx_pub = rospy.Publisher("headcenterx", UInt16, queue_size=1)
    self.headcentery_pub = rospy.Publisher("headcentery", UInt16, queue_size=1)
    self.frameskipping = rospy.get_param('~frameskipping', 1)
    self.numup = rospy.get_param('~number_of_times_to_upsample', 0)
    self.reorder_heads = rospy.get_param('~reorder_heads', False)
    self.framecount = 0 # always classifies first frame
    print("instantiated face_finder")
    rospy.loginfo('instantiated face_finder okay!')

  def callback(self,data):
    #rospy.loginfo("reached callback. that means I can read the Subscriber!")
    #print(self.framecount)
    if self.framecount%self.frameskipping is 0:
        start_time = time.time()
        self.framecount = 1
        rospy.loginfo("inside callback after passing framskipping.")
        #self.headcenterx_pub.publish(0)
        #self.headcentery_pub.publish(0)
        try:
          cv_image = self.bridge.imgmsg_to_cv2(data, "bgr8")
          rospy.loginfo("got image okay!")
        except CvBridgeError as e:
          rospy.logerr("cv_bridge failed.")
          rospy.logerr(e)
          print(e)

        # Load the jpg file into a numpy array
        #image = face_recognition.load_image_file("biden.jpg")
        #should do the trick...
        image = np.asarray(cv_image)

        # Find all the faces in the image using a pre-trained convolutional neural network.
        # This method is more accurate than the default HOG model, but it's slower
        # unless you have an nvidia GPU and dlib compiled with CUDA extensions. But if you do,
        # this will use GPU acceleration and perform well.
        # See also: find_faces_in_picture.py
        face_locations = face_recognition.face_locations(image, number_of_times_to_upsample=self.numup , model="cnn")

        rospy.loginfo("I found {} face(s) in this photograph.".format(len(face_locations)))
        thisHeadArray = HeadsArray()
        for face_location in face_locations: ### yeah, well, I will simplify this. it is already breaking too much and other people should build on top of my work, right?
            rospy.loginfo("found face.")
            # Print the location of each face in this image
            top, right, bottom, left = face_location
            thisHead = Heads()
            thisHead.top = top
            thisHead.right = right
            thisHead.bottom = bottom
            thisHead.left = left
            thisHeadArray.heads.append(thisHead)
            rospy.loginfo("A face is located at pixel location Top: {}, Left: {}, Bottom: {}, Right: {}".format(top, left, bottom, right))

            ## drawing a rectangle around every face it finds:
            #cv2.rectangle(cv_image,(top,left),(bottom,right),(0,255,0),3)

            ## You can access the actual face itself like this:
            #face_image = image[top:bottom, left:right]
            #pil_image = Image.fromarray(face_image)
            #pil_image.show()

        # if self.reorder_heads:
        #     # I will need to figure out which one is the closest to the center of the image and then sort by proximity, making sure I don't flip heads around! what a pain...
        #     rospy.logwarn('not implemented')
        #     pass
            # for i in range(0, len(thisHeadArray)):
            #     pass
        # try:
        #   #self.image_pub.publish(self.bridge.cv2_to_imgmsg(cv_image, "bgr8"))
        # except CvBridgeError as e:
        #   print(e)
        if face_locations and face_locations[0]:
          rospy.loginfo("publishing head centers")
          top, right, bottom, left = face_locations[0]
          self.headcenterx_pub.publish(np.array((left+right)/2,'uint16'))
          self.headcentery_pub.publish(np.array((top+bottom)/2,'uint16'))
          self.heads_pub.publish(thisHeadArray)
        end_time = time.time()
        total_time = end_time-start_time
        rospy.loginfo("Time used for finding these many heads was: {}\n Could run with these settings at a maximum of: {} FPS".format(total_time, 1/total_time))
    else:
        self.framecount+=1

def main(args):
  rospy.init_node('find_faces', anonymous=True)
  ic = find_faces()

  try:
    rospy.spin()
  except KeyboardInterrupt:
    print("Shutting down")
  #I'm not showing anything, so nothign to destroy
  #cv2.destroyAllWindows()

if __name__ == '__main__':
    main(sys.argv)
