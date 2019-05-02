#!/usr/bin/python

### organizes the video sets I collected with my action_recognition_experiment
### into datasets of the same style as hmdb51
import os, sys
from random import shuffle
from math import floor

origindir = sys.argv[1]
savedir = 'myset_7030splits'
os.makedirs(savedir)

for root, dirs, files in os.walk(origindir):
    containsavi = False
    print(files)
    for file in files:
        # print(file)
        filename, fileext =  os.path.splitext(file)
        if fileext == '.avi':
            containsavi = True
            break
    if containsavi:
        path = root.split(os.sep)
        print(os.path.basename(root))
        print('rootpath: %s'%root)
        name_of_action = path[-1] ###maybe something like this.
        print('Name of action: %s'%name_of_action)
        shuffle(files)
        listlen = len(files)
        #just 3 splits. hard coded. change if needed in the future; this should be easy anyway.
        #this does not guarantee that the splits will have same number of items
        split_zeros = []
        split_train = []
        split_test = []
        split_dic = []
        a, b = int(floor(listlen*.3)), int(floor(2*listlen*.3))
        print(a,b)
        split_test.append(files[0:a]) ##first third will be testing in this list
        split_test.append(files[a:b])
        split_test.append(files[b:])
        for i in range(3):
            split_train.append(list(set(files)-set(split_test[i])))
            split_zeros.append([])
            split_dic.append({})
        ### restricting so that the number of videos will be the same on every split
        #this part does.
        minnumber_of_vids_test    = min([len(spliti_test)   for spliti_test     in split_test])
        minnumber_of_vids_train   = min([len(spliti_train)  for spliti_train    in split_train])

        for i in range(3):
            split_test[i]          =  split_test[i][ 0:minnumber_of_vids_test]
            split_train[i]         =  split_train[i][0:minnumber_of_vids_train]
            split_zeros[i]         =  list((set(files)-set(split_test[i])) -set(split_train[i]))
            split_dic[i]           =  { file0:0 for file0 in split_zeros[i]}
            split_dic[i].update(      { file1:1 for file1 in split_train[i]})
            split_dic[i].update(      { file2:2 for file2 in split_test[i] })

            with open(os.path.join(savedir,'%s_test_split%d.txt'%(name_of_action,i+1)),'w') as f:
                ##go over all dictionary elements and print them into txt file
                for el, ztt in split_dic[i].iteritems():
                    f.write('%s %d\n'%(el,ztt))
