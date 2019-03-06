#!/usr/bin/env python3
#oh name collisions. we are not using PIL though, are we?
#from PIL import Image
import face_recognition
import roslib
roslib.load_manifest('face_recognition_ros')
import sys
import rospy
import cv2
from std_msgs.msg import UInt16
import sensor_msgs
from cv_bridge import CvBridge, CvBridgeError
import numpy as np

####TODO: There is a serialization error when trying to publish images. I thought it was a numpy thing, that it changed the array when I do the .asarray command, but the .dtype continues to be uint8, so I don't think that is it. I think that some other internal variable changed

class find_faces:
  ''' I don't really know how to publish a lot of head centers;
   I can use numpy ros stuff, but then cpp code will have a problem with it;
   I can set a maximum number of heads and instantiate a lot of head1, head2,
   etc stuff'''
  def __init__(self):
    #imout = rospy.get_param('~image_output', "face_overlay_image_raw")

    #self.image_pub = rospy.Publisher(imout,sensor_msgs.msg.Image, queue_size=1)
    imin = rospy.get_param('~image_input', "videofiles/image_raw")

    self.bridge = CvBridge()
    self.image_sub = rospy.Subscriber(imin,sensor_msgs.msg.Image,self.callback)

    self.headcenterx_pub = rospy.Publisher("headcenterx", UInt16, queue_size=1)
    self.headcentery_pub = rospy.Publisher("headcentery", UInt16, queue_size=1)
    self.frameskipping = rospy.get_param('~frameskipping', 1)
    self.framecount = 0 # always classifies first frame
    print("instantiated face_finder")

  def callback(self,data):
    #rospy.loginfo("reached callback. that means I can read the Subscriber!")
    #print(self.framecount)
    if self.framecount%self.frameskipping is 0:
        self.framecount = 1
        #self.headcenterx_pub.publish(0)
        #self.headcentery_pub.publish(0)
        try:
          cv_image = self.bridge.imgmsg_to_cv2(data, "bgr8")
        except CvBridgeError as e:
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
        face_locations = face_recognition.face_locations(image, number_of_times_to_upsample=0, model="cnn")

        #print("I found {} face(s) in this photograph.".format(len(face_locations)))

        for face_location in face_locations: ### yeah, well, I will simplify this. it is already breaking too much and other people should build on top of my work, right?

            # Print the location of each face in this image
            top, right, bottom, left = face_location
            print("A face is located at pixel location Top: {}, Left: {}, Bottom: {}, Right: {}".format(top, left, bottom, right))

            ## drawing a rectangle around every face it finds:
            #cv2.rectangle(cv_image,(top,left),(bottom,right),(0,255,0),3)

            ## You can access the actual face itself like this:
            #face_image = image[top:bottom, left:right]
            #pil_image = Image.fromarray(face_image)
            #pil_image.show()

        # try:
        #   #self.image_pub.publish(self.bridge.cv2_to_imgmsg(cv_image, "bgr8"))
        # except CvBridgeError as e:
        #   print(e)
        if face_locations and face_locations[0]:
          rospy.loginfo("publishing head centers")
          top, right, bottom, left = face_locations[0]
          self.headcenterx_pub.publish(np.array((left+right)/2,'uint16'))
          self.headcentery_pub.publish(np.array((top+bottom)/2,'uint16'))
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
