#!/usr/bin/env python
from flask import Flask, jsonify, abort, make_response, request, url_for
from flask import render_template
from datetime import datetime
import uuid
import redis
from tornado.wsgi import WSGIContainer
from tornado.httpserver import HTTPServer
from tornado.ioloop import IOLoop
from flask import Response

app = Flask(__name__)
application = app
r_server = redis.Redis("localhost")


@app.errorhandler(404)
def not_found(error):
    return make_response(jsonify( { 'error': 'Not found' } ), 404)

@app.route('/')
def index():
    return "These are not the droids you are looking for."

@app.route('/ttm/debug')
@app.route('/ttm/debug/<string:instance_id>')
def debug(instance_id=None):
    return render_template('debug.html', instance_id=instance_id)

@app.route('/ttm/api/v1.0/instances/<string:instance_id>/time/now', methods = ["GET"])
def utc_time(instance_id=None):
    #convert isoformat back to datetime with dateutil
    #example: dateutil.parser.parse('2013-09-26T19:38:14.399399')
    date = datetime.utcnow()
    if (instance_id):
        create_metric(instance_id, date.isoformat())
    return jsonify({"utcnow": date.isoformat()})

@app.route('/ttm/api/v1.0/instances', methods = ['GET'])
def get_instances():
    _instances = r_server.lrange('ttm_instance_ids', 0, -1)    
    instances = []
    for x in _instances:
        instances.append(
            {
                "instance_id": x
                ,"uri": url_for('get_instance_metrics', instance_id=x, _external=True) 
            } 
        )
    return jsonify( { "instances": instances } )

@app.route('/ttm/api/v1.0/instances/<string:instance_id>', methods=['GET'])
def is_instance(instance_id):
    from flask import Response
    from flask import json
    from flask import request


    ttm_start_time = ""
    ttm_end_time = ""
   
    #import pdb;pdb.set_trace()
    _metrics = r_server.lrange(instance_id, 0, -1)
    
    for metric in _metrics:
           ttm_start_time = r_server.hget(metric,'start_time')
           ttm_end_time = r_server.hget(metric,'end_time')
            
    #import pdb;pdb.set_trace() 
    if len(_metrics) == 0:
        js = {"exists": False,"start_time" : ttm_start_time, "end_time" : ttm_end_time}
    else:
        js = {"exists": True,"start_time" : ttm_start_time, "end_time" : ttm_end_time}

    callback = request.args.get('callback', '')
    if ( callback != ''):
        response = json.dumps(js)
    	response = callback + '(' + response + ');'
        return Response(response, mimetype="application/json")
    else:
	return jsonify(js)

@app.route('/ttm/api/v1.0/instances/<string:instance_id>/metrics', methods=['GET'])
def get_instance_metrics(instance_id):
    _metrics = r_server.lrange(instance_id, 0, -1)
    metrics = []
    for x in _metrics:
        metrics.append(
            {
                "id": x,
                "uri": url_for('get_metric', metric_id=x, _external=True)
            }
        )
    return jsonify( { "metrics": metrics } )

@app.route('/ttm/api/v1.0/metrics', methods = ['GET'])
def get_metrics():
    metric_ids = r_server.lrange('ttm_metric_ids', 0, -1)
    metrics = map(lambda x: r_server.hgetall(x), metric_ids)
    for metric in metrics:        
        metric['uri'] = url_for('get_metric', 
            metric_id = metric['id'], 
            _external = True)    
    return jsonify( { "metrics": metrics } )

@app.route('/ttm/api/v1.0/metrics/<string:metric_id>', methods = ["GET"])
def get_metric(metric_id):
    metric = r_server.hgetall(metric_id)
    if len(metric) == 0:
        abort(404)    
    return jsonify( { "metric": metric } )

#@app.route('/ttm/api/v1.0/instances/<string:instance_id>/metrics', methods=['POST'])
def create_metric(instance_id, date_in_isoformat):
    #This is called by utc_time
    metric_id = uuid.uuid4()
    r_server.lpush('ttm_instance_ids', instance_id)
    r_server.lpush('ttm_metric_ids', metric_id)
    r_server.lpush(instance_id, metric_id)
    metric = {                
                "id": metric_id,
                "instance_id": instance_id,
                "instance_name": "",
                "start_time": date_in_isoformat,
                "end_time": ""
    }
    r_server.hmset(metric_id, metric)

@app.route('/ttm/api/v1.0/instances/<string:instance_id>/metrics', methods=['POST'])
def update_metric(instance_id):
    if (not request.json 
        or not 'instance_name' in request.json
        or not 'end_time' in request.json):
        abort(404)
    metric_id_array = r_server.lrange(instance_id, 0, -1)
    if (not metric_id_array):
        abort(404)
    metric_id = metric_id_array[0]
    metric = r_server.hgetall(metric_id)
    metric["instance_name"] =  request.json["instance_name"]
    metric["end_time"] = request.json["end_time"]
    r_server.hmset(metric_id, metric)
    return jsonify( { 'metric': metric } ), 201

if __name__ == '__main__':
    #uncomment the next 3 lines to use tornando to serve 
    http_server = HTTPServer(WSGIContainer(app)
        , ssl_options = {
            "certfile": '/opt/OpenCloudDashboard/ssl/sslcert.cer',
            "keyfile": '/opt/OpenCloudDashboard/ssl/sslkey.key'
        }
    )
    http_server.listen(5081)
    IOLoop.instance().start()
#     app.run('0.0.0.0',debug=True, port=5081)
