#!/bin/bash
echo "Running TTM Test Cases"

curl http://localhost:5082/ttm/api/v1.0/time/now

http://localhost:5082/ttm/api/v1.0/instances/111201/time/now
http://localhost:5082/ttm/api/v1.0/instances/111202/time/now
http://localhost:5082/ttm/api/v1.0/instances/111203/time/now
http://localhost:5082/ttm/api/v1.0/instances/111204/time/now
http://localhost:5082/ttm/api/v1.0/instances/111205/time/now
http://localhost:5082/ttm/api/v1.0/instances/111206/time/now
http://localhost:5082/ttm/api/v1.0/instances/111207/time/now
http://localhost:5082/ttm/api/v1.0/instances/111208/time/now
http://localhost:5082/ttm/api/v1.0/instances/111209/time/now
http://localhost:5082/ttm/api/v1.0/instances/111210/time/now

curl -i -H "Content-Type: application/json" -X POST -d '{"instance_id":"111201","instance_name":"nk111201","start_time":"2013-11-07T23:49:56.906600","end_time":"2013-11-08T23:48:19.088958"}' http://localhost:5082/ttm/api/v1.0/instances/111201/metrics
curl -i -H "Content-Type: application/json" -X POST -d '{"instance_id":"111202","instance_name":"nk111202","start_time":"2013-11-07T23:49:56.906600","end_time":"2013-11-08T23:48:19.088958"}' http://localhost:5082/ttm/api/v1.0/instances/111202/metrics
curl -i -H "Content-Type: application/json" -X POST -d '{"instance_id":"111203","instance_name":"nk111203","start_time":"2013-11-07T23:49:56.906600","end_time":"2013-11-08T23:48:19.088958"}' http://localhost:5082/ttm/api/v1.0/instances/111203/metrics
curl -i -H "Content-Type: application/json" -X POST -d '{"instance_id":"111204","instance_name":"nk111204","start_time":"2013-11-07T23:49:56.906600","end_time":"2013-11-08T23:48:19.088958"}' http://localhost:5082/ttm/api/v1.0/instances/111204/metrics
curl -i -H "Content-Type: application/json" -X POST -d '{"instance_id":"111205","instance_name":"nk111205","start_time":"2013-11-07T23:49:56.906600","end_time":"2013-11-08T23:48:19.088958"}' http://localhost:5082/ttm/api/v1.0/instances/111205/metrics
curl -i -H "Content-Type: application/json" -X POST -d '{"instance_id":"111206","instance_name":"nk111206","start_time":"2013-11-07T23:49:56.906600","end_time":"2013-11-08T23:48:19.088958"}' http://localhost:5082/ttm/api/v1.0/instances/111206/metrics
curl -i -H "Content-Type: application/json" -X POST -d '{"instance_id":"111207","instance_name":"nk111207","start_time":"2013-11-07T23:49:56.906600","end_time":"2013-11-08T23:48:19.088958"}' http://localhost:5082/ttm/api/v1.0/instances/111207/metrics
curl -i -H "Content-Type: application/json" -X POST -d '{"instance_id":"111208","instance_name":"nk111208","start_time":"2013-11-07T23:49:56.906600","end_time":"2013-11-08T23:48:19.088958"}' http://localhost:5082/ttm/api/v1.0/instances/111208/metrics

curl -i -H "Content-Type: application/json" -X POST -d '{"instance_id":"111209","instance_name":"","start_time":"2013-11-07T23:49:56.906600","end_time":""}' http://localhost:5082/ttm/api/v1.0/instances/111209/metrics
curl -i -H "Content-Type: application/json" -X POST -d '{"instance_id":"111210","instance_name":"","start_time":"2013-11-07T23:49:56.906600","end_time":""}' http://localhost:5082/ttm/api/v1.0/instances/111210/metrics

curl http://localhost:5082/ttm/api/v1.0/incompletebuilds

curl http://localhost:5082/ttm/api/v1.0/instances/timeout
