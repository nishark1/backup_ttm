#!/bin/bash

cp ttm.upstart /etc/init/ttm.conf
ln -s /lib/init/upstart-job /etc/init.d/ttm
echo "starting ttm service"
/sbin/start ttm

cp ttm-ssl.upstart /etc/init/ttm-ssl.conf
ln -s /lib/init/upstart-job /etc/init.d/ttm-ssl
echo "starting ttm-ssl service"
/sbin/start ttm-ssl

