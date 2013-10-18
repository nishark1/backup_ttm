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

  -Post Metrics requires: 
     instance_id:request.json["instance_id"]
     instance_name:request.json["instance_name"]
     start_time:request.json["start_time"]
     end_time:request.json["end_time"]

     Curl Statement to POST Metrics Data: 
     -----------------------------------
     curl -i -H "Content-Type:application/json" -X POST -d '{"instance_id":11111, "instance_name":<instance_name>, "start_time":<start_time>, "end_time":<end_time>}' http://<host IP>/ttm/api/v1.0/metrics
   
  -List instances: 
    -/ttm/api/v1.0/instances

  -Get instance
    - /ttm/api/v1.0/instances/<string:instance_id>

  -Get time (UTC ISO Format)
      /ttm/api/v1.0/utc_time

 sequence diagram
 ================
 
 ![alt text](https://github.intel.com/jrcookli/ttm/raw/master/etc/ttm_seq.jpg "Sequence Diagram for TTM")
