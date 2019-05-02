#!/usr/bin/env python

# instantiates listeners for y and y_hat.
# get latest values, creates list and with a service call, calculates the cf

import rospy

import tot

if __name__ == '__main__':
    try:
        twrap = tot.TGatherer_wrap('trainer')
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
