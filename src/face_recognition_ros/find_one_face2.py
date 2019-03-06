#!/usr/bin/env python3
#oh name collisions. we are not using PIL though, are we?
#from PIL import Image
import face_recognition
import roslib
roslib.load_manifest('face_recognition_ros')
import sys
import rospy
import cv2
from std_msgs.msg import String
from sensor_msgs.msg import Image
from cv_bridge import CvBridge, CvBridgeError
import numpy as np

class find_faces:
  ''' I don't really know how to publish a lot of head centers;
   I can use numpy ros stuff, but then cpp code will have a problem with it;
   I can set a maximum number of heads and instantiate a lot of head1, head2,
   etc stuff'''
  def __init__(self):
    imout = rospy.get_param('~image_output', "face_overlay_image_raw")

    self.image_pub = rospy.Publisher(imout,Image, queue_size=1)
    imin = rospy.get_param('~image_input', "videofiles/image_raw")

    self.bridge = CvBridge()
    self.image_sub = rospy.Subscriber(imin,Image,self.callback)

    self.headcenterx_pub = rospy.Publisher("headcenterx", String, queue_size=1)
    self.headcentery_pub = rospy.Publisher("headcentery", String, queue_size=1)

  def callback(self,data):
    #rospy.loginfo_once("reached callback. that means I can read the Subscriber!")
    try:
      cv_image = self.bridge.imgmsg_to_cv2(data, "bgr8")
    except CvBridgeError as e:
      print(e)
      rospy.signal_shutdown('i fucked up')

    # Load the jpg file into a numpy array
    #image = face_recognition.load_image_file("biden.jpg")
    #should do the trick...
    #print('cv_image type before we use np.array')
    #print((cv_image.dtype))
    #image = np.array(cv_image, copy=True)
    image = np.asarray(cv_image)
    #print(type(image))
    #print(type(cv_image))
    # Find all the faces in the image using a pre-trained convolutional neural network.
    # This method is more accurate than the default HOG model, but it's slower
    # unless you have an nvidia GPU and dlib compiled with CUDA extensions. But if you do,
    # this will use GPU acceleration and perform well.
    # See also: find_faces_in_picture.py
    face_locations = face_recognition.face_locations(image, number_of_times_to_upsample=0, model="cnn")
    #face_locations = []
    print("I found {} face(s) in this photograph.".format(len(face_locations)))

    for face_location in face_locations:

        # Print the location of each face in this image
        top, right, bottom, left = face_location
        print("A face is located at pixel location Top: {}, Left: {}, Bottom: {}, Right: {}".format(top, left, bottom, right))

        #CAN'T GET THIS WORKING.
        ## drawing a rectangle around every face it finds:
        cv2.rectangle(cv_image,(left, top),(right, bottom),(0,255,0),3)

        ## You can access the actual face itself like this:
        #face_image = image[top:bottom, left:right]
        #pil_image = Image.fromarray(face_image)
        #pil_image.show()


        # (rows,cols,channels) = cv_image.shape
        # if cols > 60 and rows > 60 :
        #   cv2.circle(cv_image, (50,50), 10, 255)

    #cv2.imshow("Image window", cv_image)
    #cv2.waitKey(3)

    try:
        #
      #pass
#so this was failing here:
#
# <class 'float'>
# 960.0
# [ERROR] [1550750510.727832]: bad callback: <bound method find_faces.callback of <__main__.find_faces object at 0x7f20bded2ba8>>
# Traceback (most recent call last):
#   File "/root/ros_catkin_ws/install_isolated/lib/python3/dist-packages/sensor_msgs/msg/_Image.py", line 134, in serialize
#     buff.write(_get_struct_BI().pack(_x.is_bigendian, _x.step))
# struct.error: required argument is not an integer
#
# I was upset and edited /root/ros_catkin_ws/install_isolated/lib/python3/dist-packages/sensor_msgs/msg/_Image.py
# and added int() to _x.step. this worked. it is probably a bug that was fixed in a later version of sensor_msgs?



      self.image_pub.publish(self.bridge.cv2_to_imgmsg(cv_image, "bgr8"))
    except CvBridgeError as e:
      print(e)
      rospy.signal_shutdown('i fucked up')

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
