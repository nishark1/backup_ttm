#!/usr/bin/env python

import requests

VIP = "horizon-us-sw-in.icloud.intel.com"

#The following instance 1234 does exist in TTM
json_response = requests.get("http://{0}:5082/ttm/api/v1.0/instances/1234".format(VIP)).json()
if (json_response.get('exists')):
    print "ISMP worker should wait for signal from bootstrap before closing post provisioning task"

#The following instance does not exist in TTM
json_response = requests.get("http://{0}:5082/ttm/api/v1.0/instances/54321".format(VIP)).json()
if (not json_response.get('exists')):
    print "ISMP worker should immediately close the post provisioning task"

