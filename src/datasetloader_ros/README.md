# dataset loader ros
loads the hmdb51 dataset as a camera, launcher classifier in docker machine and calculates confusion matrices (kinda)

# usage

so this is actually not so easy to use.

- we need to have a route to the docker set (use addroute)

- we need to have the docker hosts available for sshing and connection with ros

export HOSTALIASES=$PWD/scripts/hosts

-> this need to be done in the same level as the execution, so that the variable is available to everyone (i.e. sourced)

another alternative is adding the hosts to /etc/hosts

- we need to set up keys for everyone with the right oHostKeyAlgorithms so that we can create a key that python-paramiko from ros can read. (done with addkeys.sh, if the hosts file is correct, or see firstlogin.sh for a simpler non-parametrized example)

After that we can test things.

In the docker, I usually do a test with opencv, so if that is not there, you need to install it. I am trying to figure out a way to do a loopback that can show the machine is working without installing opencv, but they are too many todos now and this is not a major one.

## TODO:

- add splits for ufc101 at least
- maybe the init scripst should be a part of a separate package?
