#!/usr/bin/env python
from flask import Flask, jsonify, abort, make_response, request, url_for
from flask import render_template
from datetime import datetime
import uuid
import redis
from tornado.wsgi import WSGIContainer
from tornado.httpserver import HTTPServer
from tornado.ioloop import IOLoop


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

@app.route('/ttm/api/v1.0/time/now')
def utc_time():
    #convert isoformat back to datetime with dateutil
    #example: dateutil.parser.parse('2013-09-26T19:38:14.399399')
    date = datetime.utcnow()
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
    _metrics = r_server.lrange(instance_id, 0, -1)
    if len(_metrics) == 0:
        return jsonify({"exists": False})    
    return jsonify({"exists": True})

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

@app.route('/ttm/api/v1.0/metrics', methods=['POST'])
def create_metric():
    if (not request.json 
        or not 'instance_id' in request.json
        or not 'instance_name' in request.json
        or not 'start_time' in request.json
        or not 'end_time' in request.json):
        abort(404)
    metric_id = uuid.uuid4()
    r_server.lrem('ttm_instance_ids', request.json['instance_id'], num=0)
    r_server.lpush('ttm_instance_ids', request.json['instance_id'])
    r_server.lpush('ttm_metric_ids', metric_id)
    r_server.lpush(request.json['instance_id'], metric_id)
    metric = {                
                "id": metric_id,
                "instance_id": request.json['instance_id'],
                "instance_name": request.json["instance_name"],
                "start_time": request.json["start_time"],
                "end_time": request.json["end_time"]
            }
    r_server.hmset(metric_id, metric)
    return jsonify( { 'metric': metric } ), 201

if __name__ == '__main__':
    app.run(debug = True)
    #uncomment the next 3 lines to use tornando to serve 
    #http_server = HTTPServer(WSGIContainer(app))
    #http_server.listen(5000)
    #IOLoop.instance().start()

