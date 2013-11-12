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
    ttm_logger.info("Entering utc_time API call")
    if ( instance_id != None and instance_id.find('\"') != -1):
        instance_id = instance_id.replace('\"','')

    if (instance_id):
        ttm_logger.debug('Calling create_metric with Instance Id: %s' % instance_id)
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
    ttm_logger.debug("Entering get_instance_build_status")
    _instances = r_server.lrange('ttm_instance_ids', 0, -1)
    instances = []
    instanceCount = 0
    vmfailedCount = 0
    date = datetime.utcnow()
    for x in _instances:
        try:
            instanceCount = instanceCount + 1
            ttm_logger.debug('VM count is : %s', instanceCount)
            _metrics = r_server.lrange(x, 0, -1)
            for metric in _metrics:
                ttm_start_time = r_server.hget(metric,'start_time')
                ttm_logger.debug('ttm_start_time is : %s', ttm_start_time)
                if(ttm_start_time):
                    str_ttm_start_time = ttm_start_time.split('.')
                    dt_ttm_start_time = datetime.strptime(str_ttm_start_time[0],"%Y-%m-%dT%H:%M:%S")
                    postbuild_time = datetime.utcnow() - dt_ttm_start_time

                    ttm_end_time = r_server.hget(metric,'end_time')

                ttm_instance_start_time =  r_server.hget(metric,'instance_start_time')
                ttm_logger.debug('ttm_instance_start_time is : %s', ttm_instance_start_time)
                if (ttm_instance_start_time):
                        str_ttm_instance_start_time = ttm_instance_start_time.split('.')
                        dt_ttm_instance_start_time = datetime.strptime(str_ttm_instance_start_time[0],"%Y-%m-%dT%H:%M:%S")
                        ttm_instance_name = r_server.hget(metric,'instance_name')
                        build_time = datetime.utcnow() - dt_ttm_instance_start_time

                if(((len(ttm_start_time) > 0) or (len(ttm_instance_start_time) > 0) )and (len(ttm_end_time) <= 0) ):
                    vmfailedCount = vmfailedCount + 1
                    ttm_logger.debug('Failed VM count is : %s', vmfailedCount)
                    instances.append(
                       {
                           "instance_id": x
                           ,"build_start_time":ttm_instance_start_time.__str__()
                           ,"postbuild_start_time":ttm_start_time.__str__()
                           ,"build_time":build_time.__str__()
                           ,"postbuild_time":postbuild_time.__str__()
                       }
                    )
        except:
            print 'Exception ocured: Possibly invalid datetime format'

    return jsonify( { "instances": instances , "Total_Instances":instanceCount ,"VMinPostBuildState":vmfailedCount, "CurrentTime":date.isoformat() } )


@app.route('/ttm/api/v1.0/instances/<string:instance_id>', methods=['GET'])
def is_instance(instance_id):
    from flask import Response
    from flask import json
    from flask import request

    ttm_logger.info("Entering is_instance call")

    ttm_start_time = ""
    ttm_end_time = ""
    ttm_instance_start_time = ""

    if ( instance_id != None and instance_id.find('\"') != -1):
        instance_id = instance_id.replace('\"','')
        ttm_logger.debug('Instance Id is: %s' % instance_id)

    _metrics = r_server.lrange(instance_id, 0, -1)

    for metric in _metrics:
           ttm_start_time = r_server.hget(metric,'start_time')
           ttm_logger.debug('ttm start time is: %s' % ttm_start_time)
           ttm_end_time = r_server.hget(metric,'end_time')
           ttm_logger.debug('ttm end time is: %s' % ttm_end_time)
           ttm_instance_start_time =  r_server.hget(metric,'instance_start_time')
           ttm_logger.debug('ttm instance start time is: %s' % ttm_instance_start_time)

    if len(_metrics) == 0:
        js = {"exists": False,"start_time" : ttm_start_time, "end_time" : ttm_end_time, "instance_start_time" : ttm_instance_start_time}
        ttm_logger.debug('Instance id does not exists in metrics' )
    else:
        js = {"exists": True,"start_time" : ttm_start_time, "end_time" : ttm_end_time, "instance_start_time" : ttm_instance_start_time}
        ttm_logger.debug('Instance id exists in metrics return true' )


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

def create_metric(instance_id, date_in_isoformat):
    ttm_logger.info('Entering create_metric' )
    #This is called by utc_time
    metric = {} 
    try:
        metric_id_array = r_server.lrange(instance_id, 0, -1)
        if (metric_id_array):
            metric_id = metric_id_array[0]
            metric = r_server.hgetall(metric_id)

        #if metric exists we do not want to create again
        if (metric):
            ttm_logger.debug('Metric already exists')
            pass
        else:
            ttm_logger.debug('creating Metric')
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
            ttm_logger.debug('Metric created: %s', metric)
            ttm_logger.debug('Metric created successfully')
        r_server.hmset(metric_id, metric)
    except:
        ttm_logger.error("Error occured in create metric")

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
            ttm_logger.error('Exception ocured: Possibly invalid datetime format')

    return jsonify( { "instances": instances } )

def update_metric_timeout(instance_id, instance_name,date):
    ttm_logger.info('Entering update_metric_timeout')
    try:
        if ( instance_id != None and instance_id.find('\"') != -1):
            instance_id = instance_id.replace('\"','')

        metric_id_array = r_server.lrange(instance_id, 0, -1)
        if (not metric_id_array):
            ttm_logger.debug("Instance Id is not present in the metric so aborting")
            abort(404)

        metric_id = metric_id_array[0]
        metric = r_server.hgetall(metric_id)
        metric["instance_name"] =  instance_name
        metric["end_time"] = date.isoformat()
        metric["bootstrap_timeout"] ="True"

        if (not settings.debug):
            ttm_logger.debug( "entering ISM code")
            event = TTM_Event(settings.mq_user,settings.mq_password,settings.mq_host,settings.mq_port, ssl_options=settings.mq_ssl_options,ssl=settings.mq_ssl)
            ttm_logger.debug( "event worked")
            ism_metric = {'event_type': 'compute.instance.bootstrap.end','eventType': 'Provisioning','payload': {'instance_id':metric['instance_id'] },'taskStartTime': metric['start_time'], 'taskEndTime':metric['end_time']}
            ttm_logger.debug("sending event")
            event.send_event(json.dumps(ism_metric))
            ttm_logger.debug("ISM code End")

        r_server.hmset(metric_id, metric)
    except:
         ttm_logger.error('Exception occured in update metric timeout' )

    return jsonify( { 'metric': metric } ), 201

@app.route('/ttm/api/v1.0/instances/<string:instance_id>/metrics', methods=['POST'])
def update_metric(instance_id):
    if (not request.json 
        or not 'instance_name' in request.json
        or not 'end_time' in request.json):
        abort(404)
    try:
        ttm_logger.info('Entering update_metric')
        if ( instance_id != None and instance_id.find('\"') != -1):
            instance_id = instance_id.replace('\"','')

        metric_id_array = r_server.lrange(instance_id, 0, -1)
        if (not metric_id_array):
            ttm_logger.debug("instance id does not exists in metrics so abort")
            abort(404)

        metric_id = metric_id_array[0]
        metric = r_server.hgetall(metric_id)
        metric["instance_name"] =  request.json["instance_name"]
        ttm_logger.debug('Instance name is : %s ', metric["instance_name"])
        metric["end_time"] = request.json["end_time"]
        ttm_logger.debug('End Time is : %s ', metric["end_time"])

        if (not settings.debug):
            ttm_logger.debug( "entering ISM code")
            event = TTM_Event(settings.mq_user,settings.mq_password,settings.mq_host,settings.mq_port, ssl_options=settings.mq_ssl_options,ssl=settings.mq_ssl)
            ttm_logger.debug( "event worked")
            ism_metric = {'event_type': 'compute.instance.bootstrap.end','eventType': 'Provisioning','payload': {'instance_id':metric['instance_id'] },'taskStartTime': metric['start_time'], 'taskEndTime':metric['end_time']}
            ttm_logger.debug("Sending event to ISM")
            event.send_event(json.dumps(ism_metric))
            ttm_logger.debug("ISM code End")

        r_server.hmset(metric_id, metric)
    except:
        ttm_logger.error("Exception occured in update metric")

    return jsonify( { 'metric': metric } ), 201

if __name__ == '__main__':

    LOG_FILENAME = '/var/log/ttm/_ttm.log'
    ttm_logger = logging.getLogger('TTMLogger')
    ttm_logger.setLevel(logging.DEBUG)

    handler = RotatingFileHandler(LOG_FILENAME, maxBytes=100000, backupCount=1)

    # create formatter
    formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    # add formatter to handler
    handler.setFormatter(formatter)
    #Add Handler to logger
    ttm_logger.addHandler(handler)

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



