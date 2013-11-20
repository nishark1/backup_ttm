ttm
===

Simple API to manage TTM until the Havana release of ceilometer lands

Steps to Run the Service
  - git clone the repo https://github.intel.com/jrcookli/ttm.git
  - pip install -r requirements.txt
  - sudo apt-get install redis-server

APIs:

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

  -Get instance
    - /ttm/api/v1.0/instances/<string:instance_id>

  -Get time (UTC ISO Format)
      /ttm/api/v1.0/time/now

  -Get incompletebuilds
     /ttm/api/v1.0/incompletebuilds


Sequence Diagram
================
 
 ![alt text](https://github.intel.com/jrcookli/ttm/raw/master/etc/ttm_seq.jpg "Sequence Diagram for TTM")

 
TTM Bootstrap timeout sequence Diagram
======================================

 ![alt text](https://github.intel.com/jrcookli/ttm/raw/master/etc/ttm-timeout.jpg "Sequence Diagram for TTM - Bootstrap Timeout ")
