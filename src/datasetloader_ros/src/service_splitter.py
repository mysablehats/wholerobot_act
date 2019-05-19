#!/usr/bin/env python
import rospy

from std_srvs.srv import Empty


class Splitter():
    def __init__(self,servoutlist,insrvname):
        self.services_to_call = []
        for thiservout in servoutlist:
            self.services_to_call.append(rospy.ServiceProxy(thiservout, Empty))

        rospy.Service(insrvname, Empty, self.callall)
    def callall(self,req):
        for thiservout_srv in self.services_to_call:
            thiservout_srv()
        return []

if __name__ == '__main__':
    try:
        rospy.init_node('service_splitter', log_level=rospy.INFO, anonymous=True)
        servoutlist = rospy.get_param('~services_out',['serv1','serv2'])
        insrvname = rospy.get_param('~service_in','service_in')
        mysplitter = Splitter(servoutlist, insrvname)
        rospy.spin()
    except rospy.ROSInterruptException:
        pass
