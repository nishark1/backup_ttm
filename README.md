ttm
===

Simple API to manage TTM until the Havana release of ceilometer lands

Steps to Run the Service
  - git clone the repo https://github.intel.com/jrcookli/ttm.git
  - pip install -r requirements.txt
  - sudo apt-get install redis-server

Primary APIs:

  -Get Instance Metrics:
     -/ttm/api/v1.0/instances/<string:instance_id>/metrics

  -Create Metric:
     -/ttm/api/v1.0/<instance_id>/time/now

  -Post Metrics requires: 
     instance_id:request.json["instance_id"]
     instance_name:request.json["instance_name"]
     start_time:request.json["start_time"]
     end_time:request.json["end_time"]

     Curl Statement to POST Metrics Data: 
     -----------------------------------
    curl -i -H "Content-Type: application/json" -X POST -d '{"instance_id":"111111","instance_name":"nk111111","start_time":"2013-11-07T23:49:56.906600","end_time":"2013-11-08T23:48:19.088958"}' http://localhost:5082/ttm/api/v1.0/instances/111111/metrics

   
  -List instances: 
    -/ttm/api/v1.0/instances

  -Get time (UTC ISO Format)
    - /ttm/api/v1.0/time/now

  -Check instance exists in TTM
    -  /ttm/api/v1.0/instances/<string:instance_id>
  
  -Get instances running in postbuild
    - /ttm/api/v1.0/incompletebuilds

  -To Post recipe Information
    - First time you can call when recipe starts to capture recipe start
      time. You can send any string as message like error info that you
      want to store
        --curl -X POST -d msg=<string:start_message> http://localhost:5082/ttm/api/v1.0/instances/<string:instance_id>/recipe/<string:recipe_name> 
    - Second time you can call the above to send the recipe end time
        --curl -X POST -d msg=<string:end_message> http://localhost:5082/ttm/api/v1.0/instances/<string:instance_id>/recipe
Monitoring for TTM: 
-------------------

TTM exists on same node as Horizon.
Horizon servers: az1infauto01.amr.corp.intel.com,
                 az1infauto02.amr.corp.intel.com

Monitoring Enabled for TTM to check
 - TTM service is running
 - TTM endpoint is accessible: API call is used to make sure we are able to get
   back data from TTM 



Sequence Diagram
================
 
 ![alt text](https://github.intel.com/jrcookli/ttm/raw/master/etc/ttm_seq.jpg "Sequence Diagram for TTM")


 ![alt text](https://github.intel.com/jrcookli/ttm/raw/master/etc/ttm-timeout.jpg "Sequence Diagram for TTM - Bootstrap Timeout ")
