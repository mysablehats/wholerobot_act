/*
 * Software License Agreement (Modified BSD License)
 *
 *  Copyright (c) 2016, PAL Robotics, S.L.
 *  All rights reserved.
 *
 *  Redistribution and use in source and binary forms, with or without
 *  modification, are permitted provided that the following conditions
 *  are met:
 *
 *   * Redistributions of source code must retain the above copyright
 *     notice, this list of conditions and the following disclaimer.
 *   * Redistributions in binary form must reproduce the above
 *     copyright notice, this list of conditions and the following
 *     disclaimer in the documentation and/or other materials provided
 *     with the distribution.
 *   * Neither the name of PAL Robotics, S.L. nor the names of its
 *     contributors may be used to endorse or promote products derived
 *     from this software without specific prior written permission.
 *
 *  THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
 *  "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
 *  LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS
 *  FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE
 *  COPYRIGHT OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT,
 *  INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING,
 *  BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
 *  LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
 *  CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT
 *  LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN
 *  ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
 *  POSSIBILITY OF SUCH DAMAGE.
 *
 * @author Sammy Pfeiffer
 */

//I've bastardized this guy's code. Like really. This comment and a lot of others, such as my debug messages SHOULD NOT see the light of day. No idea how to deal with modified source code (although most of the functionality here is provided by his code...)

#include <ros/ros.h>
#include <ros/console.h>
#include <image_transport/image_transport.h>
#include <camera_info_manager/camera_info_manager.h>
#include <opencv2/highgui/highgui.hpp>
#include <opencv2/imgproc/imgproc.hpp>
#include <cv_bridge/cv_bridge.h>
#include <sstream>
#include <fstream>
#include <boost/assign/list_of.hpp>
#include <boost/thread/thread.hpp>
#include <queue>
#include <mutex>
#include "datasetloader_ros/actvid.h"
#include <std_msgs/Bool.h>
#include <std_srvs/Empty.h>
#include <assert.h>
#include <signal.h>

bool DEBUG = false;//true;

std::mutex q_mutex;
std::queue<cv::Mat> framesQueue;
std::queue<cv::Mat> emptyFramesQueue;
cv::VideoCapture cap;
std::string video_stream_provider_type = "videofile";
ros::ServiceClient client;
ros::ServiceClient startonevid_client;
ros::ServiceClient stoponevid_client;
datasetloader_ros::actvid srv;
double set_camera_fps;
int max_queue_size;

// Based on the ros tutorial on transforming opencv images to Image messages

sensor_msgs::CameraInfo get_default_camera_info_from_image(sensor_msgs::ImagePtr img){
    sensor_msgs::CameraInfo cam_info_msg;
    cam_info_msg.header.frame_id = img->header.frame_id;
    // Fill image size
    cam_info_msg.height = img->height;
    cam_info_msg.width = img->width;
    ROS_INFO_STREAM("The image width is: " << img->width);
    ROS_INFO_STREAM("The image height is: " << img->height);
    // Add the most common distortion model as sensor_msgs/CameraInfo says
    cam_info_msg.distortion_model = "plumb_bob";
    // Don't let distorsion matrix be empty
    cam_info_msg.D.resize(5, 0.0);
    // Give a reasonable default intrinsic camera matrix
    cam_info_msg.K = boost::assign::list_of(1.0) (0.0) (img->width/2.0)
            (0.0) (1.0) (img->height/2.0)
            (0.0) (0.0) (1.0);
    // Give a reasonable default rectification matrix
    cam_info_msg.R = boost::assign::list_of (1.0) (0.0) (0.0)
            (0.0) (1.0) (0.0)
            (0.0) (0.0) (1.0);
    // Give a reasonable default projection matrix
    cam_info_msg.P = boost::assign::list_of (1.0) (0.0) (img->width/2.0) (0.0)
            (0.0) (1.0) (img->height/2.0) (0.0)
            (0.0) (0.0) (1.0) (0.0);
    return cam_info_msg;
}


class LockableCapture{

  //implements a simple lock to threaded playing instance
  boost::mutex mut;
  boost::condition_variable cond;
  bool new_file;

  // maybe this should be instantiated privately in the LockableCapture class? or removed;
  std_msgs::Bool nfmsg;

public:
  ros::Publisher newfilepub;
  bool autoplay;

  bool playing, hardstop;

//constructor
LockableCapture(bool ap);
//destructor
~LockableCapture() {
  // need to unlock the thread!
  //needs to be playing to get out of the
  ROS_INFO("destructor called");

  playing = true;
  cond.notify_one();
  ROS_INFO("destructor ended");

  //this should be it.
}


  bool play(std_srvs::Empty::Request &req, std_srvs::Empty::Response &res){
    playing = true;
    boost::lock_guard<boost::mutex> lock(mut);
    cond.notify_one();
    ROS_INFO("Started playing now.");
    return true;
  }

  bool stop(std_srvs::Empty::Request &req, std_srvs::Empty::Response &res){
    ROS_INFO("Stopped was called. but maybe I can't clear the lock.");

    playing = false;
    cond.notify_one();

    // boost::lock_guard<boost::mutex> lock(mut);
    // ROS_INFO("Stop: is notify_one blocking?.");

    // cond.notify_one();

    //cond.notify_all();
    // ROS_INFO("CAN clear the lock!");
    ROS_INFO("Stopped playing.");
    return true;
  }

  void do_capture(ros::NodeHandle &nh) {
    ROS_INFO("calling do_capture");

        cv::Mat frame;
        ros::Rate camera_fps_rate(set_camera_fps);

        // Read frames as fast as possible
        while (nh.ok()) {
          ROS_DEBUG("do_capture: MARCO : BEGINNING OF do_capture NHOK BIT");

          boost::unique_lock<boost::mutex> lock(mut);
          while (!playing){
            if (hardstop)
            {
              ROS_DEBUG("do_capture: NOT Clearing frame, since hardstop is on, BUT CLEARING QUEUE!");
              //MAYBE I DONT NEED TO DO THIS
              //frame.release();
              //need to clear the queue too, otherwise it doesn't work!
              //no idea what this was doing. maybe a mistake?
              //std::lock_guard<std::mutex> g(q_mutex);
              framesQueue = emptyFramesQueue;
            }
            ROS_WARN("do_capture: WAITING ON LOCK!");
            cond.wait(lock);
            ROS_DEBUG("do_capture: CLEARED LOCK");
          }
            //cap >> frame; //i suppose i could have checked for a null frame as well
            ROS_DEBUG("do_capture: ABOUT TO FRAMECAP");
            bool haveframe = cap.read(frame);
            ROS_DEBUG("do_capture: FRAMECAP OK");
            if (!haveframe)
            {
              ROS_DEBUG("do_capture: Reached the end of the video, didn't I?");
              // i can tell tsn to calculate the class now, can't i?
              std_srvs::Empty emptycallmessage;
              ROS_DEBUG("do_capture: ABOUT TO CALL STOPVID FROM CLASSIFIER");
              stoponevid_client.call(emptycallmessage); //do I need to use an empty std_srvs object here?
              ROS_DEBUG("do_capture: DONE CALLING STOPVID FROM CLASSIFIER");
              if (client.call(srv)){
                //I can tell the tsn to start accumulating scores now, can't i?
                //std_srvs::Empty emptycallmessage2;
                ROS_DEBUG("do_capture: ABOUT TO STARTVID FROM CLASSIFIER AGAIN");
                startonevid_client.call(emptycallmessage); //same as above...
                ROS_DEBUG("do_capture: DONE CALL TO STARTVID FROM CLASSIFIER");
                ROS_INFO("Got service response:\nFile: %s\nAction: %s\nActionDefined: %d  ", srv.response.File.c_str(), srv.response.Action.c_str(), srv.response.ActionDefined);
                cap.open(srv.response.File); //so im not checking to see if the file exists. we hope it does.
                ROS_DEBUG("do_capture: OPENED FILE DIDN'T BRAKE");
                haveframe = cap.read(frame);
                if (!haveframe)
                {
                  //Im stopping racing conditions. this has happened for too long!
                  ROS_WARN("do_capture: Could not acquire frame. Maybe my list is empty. Stopping play.");
                  playing = false;
                  frame.release();
                  framesQueue = emptyFramesQueue; ///del del del!
                  // boost::lock_guard<boost::mutex> lock(mut);
                  // cond.notify_all();
                  continue;
                }
                else
                {
                  ROS_DEBUG("do_capture: HAVEFRAME!");
                }
              }
              else
              {
                ROS_ERROR("do_capture: Failed to call service read_next. I'm assuming it isn't running?");
                ROS_INFO("do_capture: Stopping play.");
                playing = false;
              }
              new_file = true;
            }else{
              ROS_DEBUG("do_capture: no newfile. should I just issue a continue here to make it lock?");
              new_file = false;
            }
            ROS_DEBUG("do_capture: just before some strange publisher I am not even sure I need anymore");

            nfmsg.data = new_file;
            newfilepub.publish(nfmsg);
            if (video_stream_provider_type == "videofile")
            {
                ROS_DEBUG("do_capture: am I sleeping for too long? ");

                camera_fps_rate.sleep();
            }
            ROS_DEBUG("do_capture: just before the frame pusher guy. ");

            if(!frame.empty()) {
                ROS_DEBUG("do_capture: not my lock... ");
                std::lock_guard<std::mutex> g(q_mutex);
                // accumulate only until max_queue_size
                ROS_DEBUG("do_capture: cleared not my LOCK");
                if (framesQueue.size() < max_queue_size) {
                    framesQueue.push(frame.clone());
                    ROS_DEBUG("do_capture: done pushing fram to queue, but queue was full!");
                }
                // once reached, drop the oldest frame
                else {
                    framesQueue.pop();
                    framesQueue.push(frame.clone());
                    ROS_DEBUG("do_capture: done pushing fram to queue. queue was okay");
                }
            }
            ROS_DEBUG("do_capture: POLO: END OF do_capture NHOK BIT ");
            ros::spinOnce();
        }

        ROS_WARN("do_capture: AM I REACHING HERE?");
  }
};

LockableCapture::LockableCapture(bool ap) {
  ROS_INFO("instanciated object");
  autoplay = ap;

  if (autoplay){
    playing = true;
    boost::lock_guard<boost::mutex> lock(mut);
    cond.notify_one();
    ROS_INFO("Autoplay is defined. Started playing now.");
  }

  // we don't want it to start and play so
  playing = false;
}


void sighand(int sig, LockableCapture* obj)
{
  //got a signal,, call the destructor for the queue and call it a day.
  ROS_INFO("shutting down!");
  delete obj;
  ros::shutdown();
}

int main(int argc, char** argv)
{
    // set debugging level to DEBUG
    if (DEBUG)
    {
      if( ros::console::set_logger_level(ROSCONSOLE_DEFAULT_NAME, ros::console::levels::Debug) ) {
         ros::console::notifyLoggerLevelsChanged();
      }
    }

    ros::init(argc, argv, "image_publisher");
    ros::NodeHandle nh;

    ros::NodeHandle _nh("~"); // to get the private params
    image_transport::ImageTransport it(nh);
    image_transport::CameraPublisher pub = it.advertiseCamera("camera", 1);

    std::string readnextsrvhandle;
    std::string classifiernamespace;
     _nh.param<std::string>("readnext_service_handle",readnextsrvhandle,"/readpathnode/read_next");
     _nh.param<std::string>("classifier_namespace",classifiernamespace,"");

    client = _nh.serviceClient<datasetloader_ros::actvid>(readnextsrvhandle);
    startonevid_client = _nh.serviceClient<std_srvs::Empty>("start_vidscores");
    stoponevid_client = _nh.serviceClient<std_srvs::Empty>("stop_vidscores");

    bool autoplay;
    _nh.param<bool>("autoplay", autoplay, true);

    LockableCapture mylockablecap(autoplay);
    LockableCapture* p;
    // auto mysighand = [=](int sig){
    //   ROS_INFO("shutting down!");
    //   delete p;
    //   ros::shutdown();
    //  };
    // //let's override the ros signal_shutdown and register our custom signal handler as the other thread was not being killed.
    // signal(SIGINT, mysighand); //this is a tough one. i think it should be a class with a vector of sigterms inside and we append to it when we create an object, or something like that. Need to read upon it.
    ros::ServiceServer service_play = _nh.advertiseService("play", &LockableCapture::play, &mylockablecap);
    ros::ServiceServer service_stop = _nh.advertiseService("stop", &LockableCapture::stop, &mylockablecap);

    ROS_INFO("autoplay %d",  mylockablecap.autoplay);
    mylockablecap.newfilepub = _nh.advertise<std_msgs::Bool>("new_file",1);
    _nh.param<bool>("publish_nothing_when_stopped", mylockablecap.hardstop,true);
    ROS_INFO("hardstooop %d",mylockablecap.hardstop);

    double fps;
    _nh.param<double>("fps", fps, 240.0);
    ros::Rate r(fps);


    while (!mylockablecap.playing){
        ROS_INFO_ONCE("Thread is locked. Not playing.");
        ros::spinOnce();
        r.sleep();
    }

    if (client.call(srv)){

      ROS_INFO("Got service response:\nFile: %s\nAction: %s\nActionDefined: %d  ", srv.response.File.c_str(), srv.response.Action.c_str(), srv.response.ActionDefined);
    }
    else
    {
      ROS_ERROR("Failed to call service read_next.");
      return 1;
    }
    cap.open(srv.response.File); //so im not checking to see if the file exists. we hope it does.

    while(!cap.isOpened()){
      ROS_WARN_THROTTLE(10,"Did not receive a file from service. Is read_next running?");
      ros::spinOnce();
      r.sleep();
      client.call(srv);
      cap.open(srv.response.File);
    }

    ROS_INFO_STREAM("Video stream provider type detected: " << video_stream_provider_type);

    std::string camera_name;
    _nh.param("camera_name", camera_name, std::string("camera"));
    ROS_INFO_STREAM("Camera name: " << camera_name);

    _nh.param("set_camera_fps", set_camera_fps, 30.0);
    ROS_INFO_STREAM("Setting camera FPS to: " << set_camera_fps);
    cap.set(CV_CAP_PROP_FPS, set_camera_fps);

    double reported_camera_fps;
    // OpenCV 2.4 returns -1 (instead of a 0 as the spec says) and prompts an error
    // HIGHGUI ERROR: V4L2: Unable to get property <unknown property string>(5) - Invalid argument
    reported_camera_fps = cap.get(CV_CAP_PROP_FPS);
    if (reported_camera_fps > 0.0)
        ROS_INFO_STREAM("Camera reports FPS: " << reported_camera_fps);
    else
        ROS_INFO_STREAM("Backend can't provide camera FPS information");

    int buffer_queue_size;
    _nh.param("buffer_queue_size", buffer_queue_size, 100);
    ROS_INFO_STREAM("Setting buffer size for capturing frames to: " << buffer_queue_size);
    max_queue_size = buffer_queue_size;

    // double fps;
    // _nh.param("fps", fps, 240.0);
    ROS_INFO_STREAM("Throttling to fps: " << fps);

    std::string frame_id;
    _nh.param("frame_id", frame_id, std::string("camera"));
    ROS_INFO_STREAM("Publishing with frame_id: " << frame_id);

    std::string camera_info_url;
    _nh.param("camera_info_url", camera_info_url, std::string(""));
    ROS_INFO_STREAM("Provided camera_info_url: '" << camera_info_url << "'");

    bool flip_horizontal;
    _nh.param("flip_horizontal", flip_horizontal, false);
    ROS_INFO_STREAM("Flip horizontal image is: " << ((flip_horizontal)?"true":"false"));

    bool flip_vertical;
    _nh.param("flip_vertical", flip_vertical, false);
    ROS_INFO_STREAM("Flip vertical image is: " << ((flip_vertical)?"true":"false"));

    int width_target;
    int height_target;
    _nh.param("width", width_target, 0);
    _nh.param("height", height_target, 0);
    if (width_target != 0 && height_target != 0){
        ROS_INFO_STREAM("Forced image width is: " << width_target);
        ROS_INFO_STREAM("Forced image height is: " << height_target);
    }

    // From http://docs.opencv.org/modules/core/doc/operations_on_arrays.html#void flip(InputArray src, OutputArray dst, int flipCode)
    // FLIP_HORIZONTAL == 1, FLIP_VERTICAL == 0 or FLIP_BOTH == -1
    bool flip_image = true;
    int flip_value;
    if (flip_horizontal && flip_vertical)
        flip_value = -1; // flip both, horizontal and vertical
    else if (flip_horizontal)
        flip_value = 1;
    else if (flip_vertical)
        flip_value = 0;
    else
        flip_image = false;

    if(!cap.isOpened()){
        ROS_ERROR_STREAM("Could not open the stream.");
        return -1;
    }
    if (width_target != 0 && height_target != 0){
        cap.set(CV_CAP_PROP_FRAME_WIDTH, width_target);
        cap.set(CV_CAP_PROP_FRAME_HEIGHT, height_target);
    }

    cv::Mat frame;
    sensor_msgs::ImagePtr msg;
    sensor_msgs::CameraInfo cam_info_msg;
    std_msgs::Header header;
    header.frame_id = frame_id;
    camera_info_manager::CameraInfoManager cam_info_manager(nh, camera_name, camera_info_url);
    // Get the saved camera info if any
    cam_info_msg = cam_info_manager.getCameraInfo();
    cam_info_msg.header = header;

    ROS_INFO_STREAM("Opened the stream, starting to publish.");
    boost::thread cap_thread(boost::bind(&LockableCapture::do_capture, &mylockablecap, nh));

    while (nh.ok()) {
       ROS_DEBUG("MARCO : BEGINNING OF mainloop NHOK BIT");

        {
            std::lock_guard<std::mutex> g(q_mutex);
            if(mylockablecap.hardstop&&!mylockablecap.playing){
              // ROS_DEBUG("i'm not playing. i need to clear the current frame, or it will get published. ");
              frame.release();
              //frame = framesQueue.front();
              //or i don't need to clear the queue at all since this is an empty frame anyway....
              //ROS_INFO_STREAM("reached the assertiong bit. ");

              //assert(frame.empty());
            }
            else
            {
              if (!framesQueue.empty()){
                // ROS_DEBUG("quack");
                  frame = framesQueue.front();
                  // ROS_DEBUG("dumbo");
                  framesQueue.pop();
                  // ROS_DEBUG("pop");
              }
            }
        }

        if (pub.getNumSubscribers() > 0){
            // ROS_DEBUG("which statement fails? ");
            // Check if grabbed frame is actually filled with some content
            if(!frame.empty()) {
                // Flip the image if necessary
                // ROS_DEBUG("bob");
                if (flip_image)
                    cv::flip(frame, frame, flip_value);
                // ROS_DEBUG("torpedo ");
                msg = cv_bridge::CvImage(header, "bgr8", frame).toImageMsg();
                // ROS_DEBUG("papaya");
                // Create a default camera info if we didn't get a stored one on initialization
                if (cam_info_msg.distortion_model == ""){
                    ROS_WARN_STREAM("No calibration file given, publishing a reasonable default camera info.");
                    cam_info_msg = get_default_camera_info_from_image(msg);
                    cam_info_manager.setCameraInfo(cam_info_msg);
                }
                // The timestamps are in sync thanks to this publisher
                  //ROS_INFO_STREAM("do i reach the publisher bit?. ");
                  // ROS_DEBUG("amoeba");
                  pub.publish(*msg, cam_info_msg, ros::Time::now());
                  // ROS_DEBUG("giant bob ");

            }

            ros::spinOnce();
        }
        r.sleep();
        // ROS_DEBUG("POLO : END OF mainloop NHOK BIT");

    }
    delete p;
    // rosdebug statements will no longer work here because ros is shutdown!
    // ROS_DEBUG("before cap_thread.join");
    cap_thread.join();
}
