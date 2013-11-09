#!/usr/bin/env python
#for ism event publishing
from ttm_event import TTM_Event
import pika
from flask import Flask, jsonify, abort, make_response, request, url_for
from flask import render_template
from datetime import datetime
import uuid
import redis
import sys
from tornado.wsgi import WSGIContainer
from tornado.httpserver import HTTPServer
from tornado.ioloop import IOLoop
from flask import Response
import json
import settings
import logging
from logging.handlers import RotatingFileHandler
from OpenSSL import SSL

app = Flask(__name__)
application = app
r_server = redis.Redis(settings.redis_host)

@app.errorhandler(404)
def not_found(error):
    return make_response(jsonify( { 'error': 'Not found' } ), 404)

@app.route('/')
def index():
    app.logger.warning('A warning occurred (%d apples)', 42)
    app.logger.error('An error occurred')
    app.logger.info('Info')
    return "These are not the droids you are looking for."

@app.route('/ttm/debug')
@app.route('/ttm/debug/<string:instance_id>')
def debug(instance_id=None):
    return render_template('debug.html', instance_id=instance_id)

@app.route('/ttm/api/v1.0/instances/<string:instance_id>/time/now', methods = ["GET"])
@app.route('/ttm/api/v1.0/time/now', methods = ["GET"])
def utc_time(instance_id=None):
    #convert isoformat back to datetime with dateutil
    #example: dateutil.parser.parse('2013-09-26T19:38:14.399399')
    date = datetime.utcnow()
    
    if ( instance_id != None and instance_id.find('\"') != -1):
        instance_id = instance_id.replace('\"','')

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

@app.route('/ttm/api/v1.0/incompletebuilds', methods = ['GET'])
def get_instances_build_status():
    from datetime import datetime

    _instances = r_server.lrange('ttm_instance_ids', 0, -1)    
    instances = []
    for x in _instances:
       _metrics = r_server.lrange(x, 0, -1)
       #date = datetime.utcnow()
       for metric in _metrics:
           ttm_start_time = r_server.hget(metric,'start_time')
           str_ttm_start_time = ttm_start_time.split('.')
           dt_ttm_start_time = datetime.strptime(str_ttm_start_time[0],"%Y-%m-%dT%H:%M:%S")
           postbuild_time = datetime.utcnow() - dt_ttm_start_time

           ttm_end_time = r_server.hget(metric,'end_time')

           ttm_instance_start_time =  r_server.hget(metric,'instance_start_time')
           if (ttm_instance_start_time):
               str_ttm_instance_start_time = ttm_instance_start_time.split('.')
               dt_ttm_instance_start_time = datetime.strptime(str_ttm_instance_start_time[0],"%Y-%m-%dT%H:%M:%S")
               ttm_instance_name = r_server.hget(metric,'instance_name')
               build_time = datetime.utcnow() - dt_ttm_instance_start_time

           if(((len(ttm_start_time) > 0) or (len(ttm_instance_start_time) > 0) )and (len(ttm_end_time) <= 0) ):
               instances.append(
                       {
                           "instance_id": x
                           ,"build_start_time":ttm_instance_start_time.__str__()
                           ,"postbuild_start_time":ttm_start_time.__str__()
                           ,"build_time":build_time.__str__()
                           ,"postbuild_time":postbuild_time.__str__()
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
    ttm_instance_start_time = ""

    if ( instance_id != None and instance_id.find('\"') != -1):
        instance_id = instance_id.replace('\"','')

    #import pdb;pdb.set_trace()
    if ( instance_id != None and instance_id.find('\"') != -1):
        instance_id = instance_id.replace('\"','')

    _metrics = r_server.lrange(instance_id, 0, -1)

    for metric in _metrics:
           ttm_start_time = r_server.hget(metric,'start_time')
           ttm_end_time = r_server.hget(metric,'end_time')
           ttm_instance_start_time =  r_server.hget(metric,'instance_start_time')

    #import pdb;pdb.set_trace() 
    if len(_metrics) == 0:
        js = {"exists": False,"start_time" : ttm_start_time, "end_time" : ttm_end_time, "instance_start_time" : ttm_instance_start_time}
    else:
        js = {"exists": True,"start_time" : ttm_start_time, "end_time" : ttm_end_time, "instance_start_time" : ttm_instance_start_time}

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
    metric = {} 
    metric_id_array = r_server.lrange(instance_id, 0, -1)
    if (metric_id_array):
            metric_id = metric_id_array[0]
            metric = r_server.hgetall(metric_id)

    if (metric):
        pass
    else:

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
                "end_time": "",
                "instance_start_time": date_in_isoformat,
                "bootstrap_timeout":False
        }
    r_server.hmset(metric_id, metric)


@app.route('/ttm/api/v1.0/instances/timeout', methods=['GET'])
def check_timeout_vm():
    _instances = r_server.lrange('ttm_instance_ids', 0, -1)
    instances = []
    hours = 0
    minutes = 0
    bhours = 0
    
    for x in _instances:
        try:
            _metrics = r_server.lrange(x, 0, -1)
            for metric in _metrics:
                ttm_start_time = r_server.hget(metric,'start_time')
                if(ttm_start_time):
                    str_ttm_start_time = ttm_start_time.split('.')
                    dt_ttm_start_time = datetime.strptime(str_ttm_start_time[0],"%Y-%m-%dT%H:%M:%S")
                    postbuild_time = datetime.utcnow() - dt_ttm_start_time
                    hours = (postbuild_time.days*24)-(postbuild_time.seconds/3600)
                    print '{} hours'.format(hours)

                ttm_instance_start_time =  r_server.hget(metric,'instance_start_time')
                if (ttm_instance_start_time):
                    str_ttm_instance_start_time = ttm_instance_start_time.split('.')
                    dt_ttm_instance_start_time = datetime.strptime(str_ttm_instance_start_time[0],"%Y-%m-%dT%H:%M:%S")
                    build_time = datetime.utcnow() - dt_ttm_instance_start_time
                    bhours = (build_time.days*24)-(build_time.seconds/3600)
                    print '{} hours'.format(hours)

                ttm_end_time = r_server.hget(metric,'end_time')
                date = datetime.utcnow()
                instance_name = r_server.hget(metric,'instance_name')
                if(((hours > 3) and (ttm_end_time == ""))
                            or ((bhours > 3) and (ttm_end_time == ""))):
                    update_metric_timeout(x, instance_name,date)
                    instances.append(
                        {
                            "instance_id": x
                            ,"instance_name":instance_name
                            ,"start_time":ttm_start_time
                            ,"instance_start_time":ttm_instance_start_time
                            ,"end_time":date.isoformat()
                            ,"bootstrap_timeout":True
                        }
                    )
        except:
            print 'Exception ocured: Possibly invalid datetime format'

    return jsonify( { "instances": instances } )

def update_metric_timeout(instance_id, instance_name,date):
    if ( instance_id != None and instance_id.find('\"') != -1):
        instance_id = instance_id.replace('\"','')

    metric_id_array = r_server.lrange(instance_id, 0, -1)
    if (not metric_id_array):
        abort(404)

    metric_id = metric_id_array[0]
    metric = r_server.hgetall(metric_id)
    metric["instance_name"] =  instance_name
    metric["end_time"] = date.isoformat()
    metric["bootstrap_timeout"] ="True"


    if (not settings.debug):
        print "entering ISM code"
        event = TTM_Event(settings.mq_user,settings.mq_password,settings.mq_host,settings.mq_port, ssl_options=settings.mq_ssl_options,ssl=settings.mq_ssl)
        print "event worked"
        ism_metric = {'event_type': 'compute.instance.bootstrap.end','eventType': 'Provisioning','payload': {'instance_id':metric['instance_id'] },'taskStartTime': metric['start_time'], 'taskEndTime':metric['end_time']}
        print "sending event"
        event.send_event(json.dumps(ism_metric))
        print "ISM code End"

    r_server.hmset(metric_id, metric)
    return jsonify( { 'metric': metric } ), 201

@app.route('/ttm/api/v1.0/instances/<string:instance_id>/metrics', methods=['POST'])
def update_metric(instance_id):
    if (not request.json 
        or not 'instance_name' in request.json
        or not 'end_time' in request.json):
        abort(404)

    if ( instance_id != None and instance_id.find('\"') != -1):
        instance_id = instance_id.replace('\"','')

    metric_id_array = r_server.lrange(instance_id, 0, -1)
    if (not metric_id_array):
        abort(404)

    metric_id = metric_id_array[0]
    metric = r_server.hgetall(metric_id)
    metric["instance_name"] =  request.json["instance_name"]
    metric["end_time"] = request.json["end_time"]

    if (not settings.debug):
        print "entering ISM code"
        event = TTM_Event(settings.mq_user,settings.mq_password,settings.mq_host,settings.mq_port, ssl_options=settings.mq_ssl_options,ssl=settings.mq_ssl)
        print "event worked" 
        ism_metric = {'event_type': 'compute.instance.bootstrap.end','eventType': 'Provisioning','payload': {'instance_id':metric['instance_id'] },'taskStartTime': metric['start_time'], 'taskEndTime':metric['end_time']}
        print "Sending event to ISM"
        event.send_event(json.dumps(ism_metric))
        print "ISM code End"

    r_server.hmset(metric_id, metric)
    return jsonify( { 'metric': metric } ), 201

if __name__ == '__main__':

    handler = RotatingFileHandler('/var/log/ttm/_ttm.log', maxBytes=100000, backupCount=1)
    handler.setLevel(logging.INFO)
    app.logger.addHandler(handler)

    #uncomment the next 3 lines to use tornando to serve
    if (sys.argv and len(sys.argv) > 1 and sys.argv[1] == "ssl"):
    #   https_server = HTTPServer(WSGIContainer(app)
    #      , ssl_options = {
    #           "certfile": '/opt/OpenCloudDashboard/ssl/sslcert.cer',
    #           "keyfile": '/opt/OpenCloudDashboard/ssl/sslkey.key'
    #       }
    #   )
    #   https_server.listen(5081)
    #   IOLoop.instance().start()
        context = SSL.Context(SSL.SSLv23_METHOD)
        context.use_privatekey_file('/opt/OpenCloudDashboard/ssl/sslkey.key')
        context.use_certificate_file('/opt/OpenCloudDashboard/ssl/sslcert.cer')
        app.run(host=settings.listen_ip, port=5081, debug=True, ssl_context=context)

    else:
       http_server = HTTPServer(WSGIContainer(app))
       http_server.listen(5082, address=settings.listen_ip)
       IOLoop.instance().start()

    #uncomment the next 3 lines to use tornando to serve 



