#!/usr/bin/env python
import rospy
import caffe_tsn_ros.msg
import matplotlib.pyplot as plt
from matplotlib import animation
import numpy as np
from threading import Lock
import time

mylock = Lock()
# actions = np.arange(51)
# currdata = 0.01* np.random.rand(len(actions))

def get_vals(data):
    global currdata, actions
    output = []
    las = []
    for act in data.actions:
        las.append(act.action)
        output.append(act.confidence)
    with mylock:

        currdata = output
        actions = las
        #rospy.logwarn(len(currdata))
        #rospy.logwarn(len(actions))

def barlist(n):
#    return  np.random.rand(len(actions))
    with mylock:
        outdata = currdata
        #oulabels = curraxeslabels
        #print(len(currdata))
    return currdata #, #curraxeslabels

def animate(i):
    y=barlist(i+1)
    for i, b in enumerate(barcollection):
        b.set_width(y[i])

    return barcollection

rospy.init_node('actgraph_node', anonymous=True)

rospy.loginfo('Waiting for ActionDic to be published')
init_ms = rospy.wait_for_message('/act', caffe_tsn_ros.msg.ActionDic)
get_vals(init_ms)
rospy.loginfo('ActionDic is publishing.')

ms = rospy.Subscriber('/act', caffe_tsn_ros.msg.ActionDic, get_vals, queue_size=1)

plot_title = rospy.get_param('~title','mytitle')
plot_bar_color = rospy.get_param('~bar_color','green')


fig, ax = plt.subplots(num=plot_title)

y_pos = np.arange(len(actions))

barcollection = plt.barh(y_pos,barlist(1), align='center',
        color=plot_bar_color, ecolor='black')

ax.set_yticks(y_pos)
ax.set_yticklabels(actions)
ax.invert_yaxis()  # labels read top-to-bottom
ax.set_xlabel('Confidence')
ax.set_title('Action confidence levels')
ax.set_xlim([0,1])


anim=animation.FuncAnimation(fig,animate,repeat=False,blit=True,interval=50)
#,frames=n,
#                             interval=40)

#anim.save('mymovie.mp4',writer=animation.FFMpegWriter(fps=10))
plt.show()
