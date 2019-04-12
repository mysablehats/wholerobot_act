#!/usr/bin/env python
import rospy
import message_filters
import caffe_tsn_ros.msg
import matplotlib.pyplot as plt
from matplotlib import animation
import numpy as np
from threading import Lock
import time
from math import sqrt
mylock = Lock()
stopped = True

def get_classes(data):
    global actions
    las = []
    for act in data.actions:
        las.append(act.action)
    with mylock:
        actions = las

def get_vals(data1r,data1f,data2r,data2f,data3r, data3f):
    print('HERE!')
    global yil
    i = 0
    output = []
    with mylock:
        for data in [data1r,data1f,data2r,data2f,data3r, data3f]:
            for act in data.actions:
                output.append(act.confidence)

            yil[i] = output
            i = i+1
        stopped = False
    #print(yil)
            #rospy.logwarn(len(currdata))
            #rospy.logwarn(len(actions))

def animate(i):
    print('animate!')
    with mylock:
        yill.append(np.array(yil))
    if len(yill)>averageN:
        yill.pop(0)
    ylmeans = []
    for yl in yill:
        try:
            ylmeans.append(yl.prod(axis=0))
        except:
            print(yl.shape())
            print(type(yl))
    y = np.array(ylmeans).max(axis=0)
    #print('y: {}'.format(y))
    for i, b in enumerate(barcollection):
        #print(dir(b))
#    for i, b,j,c in zip(enumerate(barcollection),enumerate(ax.errorbar)):
        b.set_width(sqrt(y[i]))
        #b.set_height(sqrt((y1[i]+1/len(actions))*(y2[i]+1/len(actions))))
        #b.errorbar(err[i])
#        assert(i == j)
#        c.x = err[j]# y[j]
        #c#.
    return barcollection

rospy.init_node('actgraph_node', anonymous=True)

rospy.loginfo('Waiting for ActionDic to be published')
init_ms = rospy.wait_for_message('/rgb1', caffe_tsn_ros.msg.ActionDic)
get_classes(init_ms)

rospy.loginfo('ActionDic is publishing.')

ss = []
yil = []
yill = []
for i in range(1,4):
    yil.append([])
    yil.append([])
    ss.append(message_filters.Subscriber('/rgb{}'.format(i) , caffe_tsn_ros.msg.ActionDic, queue_size=1))
    ss.append(message_filters.Subscriber('/flow{}'.format(i), caffe_tsn_ros.msg.ActionDic, queue_size=1))

ts = message_filters.ApproximateTimeSynchronizer(ss, 10,1)
ts.registerCallback( get_vals)

plot_title = rospy.get_param('~title','allcombined')
plot_bar_color = rospy.get_param('~bar_color','green')
averageN = rospy.get_param('~N',3)


fig, ax = plt.subplots(num=plot_title)

y_pos = np.arange(len(actions))

barcollection = plt.barh(y_pos, 0.01* np.random.rand(len(actions)), align='center', #xerr=barlist2(1),
        color=plot_bar_color, ecolor='black')

#print(dir(barcollection))
ax.set_yticks(y_pos)
ax.set_yticklabels(actions)
ax.invert_yaxis()  # labels read top-to-bottom
ax.set_xlabel('Confidence')
ax.set_title('Action confidence levels')
ax.set_xlim([0,1])

time.sleep(2)

anim=animation.FuncAnimation(fig,animate,repeat=False,blit=True,interval=150)
#,frames=n,
#                             interval=40)

#anim.save('mymovie.mp4',writer=animation.FFMpegWriter(fps=10))
plt.show()









#
#
#
#
#
#
#
#
#
#
#
# def animate(i):
#     y1=currdata
#     y2=currdata2
#     y1l.append(y1)
#     if len(y1l)>averageN:
#         y1l.pop(0)
#     y2l.append(y2)
#     if len(y2l)>averageN:
#         y2l.pop(0)
#     y1a = np.array(y1l)
#     y2a = np.array(y2l)
#     y1mean = y1a.sum(axis=0)/len(actions)
#     y2mean = y2a.sum(axis=0)/len(actions)
#     for i, b in enumerate(barcollection):
#         #print(dir(b))
# #    for i, b,j,c in zip(enumerate(barcollection),enumerate(ax.errorbar)):
#         b.set_width(y1mean[i]*y2mean[i])
#         #b.set_height(sqrt((y1[i]+1/len(actions))*(y2[i]+1/len(actions))))
#         #b.errorbar(err[i])
# #        assert(i == j)
# #        c.x = err[j]# y[j]
#         #c#.
#     return barcollection
