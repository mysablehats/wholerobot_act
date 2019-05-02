#!/usr/bin/python

### organizes the video sets I collected with my action_recognition_experiment
### into datasets of the same style as hmdb51
import os, sys, subprocess
from shutil import copyfile

origindir = sys.argv[1]

destdir = 'myset'
os.makedirs(destdir)


for root, dirs, files in os.walk(origindir):
    path = root.split(os.sep)
    print(os.path.basename(root))
    print('rootpath: %s'%root)
    for file in files:
        print(file)
        filename, fileext =  os.path.splitext(file)
        if 'image_' in filename:
            filename = filename.split('image_')[1]
        if fileext == '.avi' and not 'depth' in os.path.join(root,file):
            name_end = 0
            ## now play the file to see if this is the correct activity or not:
            subprocess.call(['vlc','--qt-minimal-view','-q','--play-and-exit',os.path.join(root,file)])
            res = raw_input('Is this the right category [y,n]')
            while not (res == 'y' or res == 'n'):
                  res = raw_input('Is this the right category [y,n]')
            if res == 'n':
                filename = 'misc'
            if not os.path.exists(os.path.join(destdir,filename)):
                os.makedirs(os.path.join(destdir,filename))

            while(os.path.exists(os.path.join(destdir,filename,filename+'_'+str(name_end)+fileext))):
                name_end = name_end +1

            copyfile(os.path.join(root,file),os.path.join(destdir,filename,filename+'_'+str(name_end)+fileext))
