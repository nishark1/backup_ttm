#!/bin/bash

cp ttm.upstart /etc/init/ttm.conf
ln -s /lib/init/upstart-job /etc/init.d/ttm
echo "starting ttm service"
start ttm
echo "that's all folks"

#cp ism.upstart /etc/init/ism.conf
#ln -s /lib/init/upstart-job /etc/init.d/ism
#echo "starting ism service"
#start ism
#echo "that's all folks"
