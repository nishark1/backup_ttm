#!/bin/bash

cp ttm.upstart /etc/init/ttm.conf
ln -s /lib/init/upstart-job /etc/init.d/ttm
echo "starting ttm service"
start ttm

cp ttm-ssl.upstart /etc/init/ttm-ssl.conf
ln -s /lib/init/upstart-job /etc/init.d/ttm-ssl
echo "starting ttm-ssl service"
start ttm-ssl

