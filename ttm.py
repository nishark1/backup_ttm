#!/usr/bin/env python
#for ism event publishing
from ttm_event import TTM_Event
import pika
from flask import Flask, jsonify, abort, make_response, request, url_for
from flask import render_template
from datetime import datetime, timedelta
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
        except Exception as e:
            ttm_logger.error(e)

    return jsonify( { "instances": instances , "Total_Instances":instanceCount ,"VMinPostBuildState":vmfailedCount, "CurrentTime":date.isoformat() } )


@app.route('/ttm/api/v1.0/instances/<string:instance_id>', methods=['GET'])
def is_instance(instance_id):
    #from flask import Response
    #from flask import json
    #from flask import request

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
            #The second time we are called is from within the bootstrap :)
            metric["bootstrap_start_time"] = date_in_isoformat
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
                "bootstrap_start_time": "",
                "end_time": "",
                "instance_start_time": date_in_isoformat,
                "bootstrap_timeout":False,
                "mute":False
            }
            ttm_logger.debug('Metric created: %s', metric)
            ttm_logger.debug('Metric created successfully')
        r_server.hmset(metric_id, metric)
    except:
        ttm_logger.exception("Error occured in create metric")
        raise

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
                    ttm_logger.debug("Capturing end time for reference before calculating postbuild_time")
                    ttm_logger.debug(datetime.utcnow())
                    ttm_logger.debug("Calculating PostBuild time : ")
                    postbuild_time = datetime.utcnow() - dt_ttm_start_time
                    ttm_logger.debug(postbuild_time)
                    hours = postbuild_time.total_seconds() / 3600
                    ttm_logger.debug(hours)
                    #print '{} hours'.format(hours)

                ttm_instance_start_time =  r_server.hget(metric,'instance_start_time')
                if (ttm_instance_start_time):
                    str_ttm_instance_start_time = ttm_instance_start_time.split('.')
                    dt_ttm_instance_start_time = datetime.strptime(str_ttm_instance_start_time[0],"%Y-%m-%dT%H:%M:%S")
                    ttm_logger.debug("Capturing end time for reference before calculating build_time")
                    ttm_logger.debug(datetime.utcnow())
                    ttm_logger.debug("Calculating Build time : ")
                    build_time = datetime.utcnow() - dt_ttm_instance_start_time
                    ttm_logger.debug(build_time)
                    bhours = build_time.total_seconds() / 3600
                    ttm_logger.debug(bhours)
                    #print '{} hours'.format(hours)

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
            ttm_logger.debug('Exception ocured: Possibly invalid datetime format')

    return jsonify( { "instances": instances, "current_time": date.isoformat() } )

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

        if (hasattr(settings,"debug") and not settings.debug):
            ttm_logger.debug("we are in debug but would normally talk to ISM here")
        else:
            ttm_logger.debug( "entering ISM code")
            event = TTM_Event(settings.mq_user,settings.mq_password,settings.mq_host,settings.mq_port, ssl_options=settings.mq_ssl_options,ssl=settings.mq_ssl)
            ttm_logger.debug( "event worked")
            ism_metric = {'event_type': 'compute.instance.bootstrap.end','eventType': 'Provisioning','payload': {'instance_id':metric['instance_id'] },'taskStartTime': metric['start_time'], 'taskEndTime':metric['end_time']}
            ttm_logger.debug("sending event")
            ttm_logger.debug(ism_metric)
            event.send_event(json.dumps(ism_metric))
            ttm_logger.debug("ISM code End")

        r_server.hmset(metric_id, metric)

    except Exception as e:
        ttm_logger.exception('Exception occured in update metric timeout' )
        raise

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

        if (hasattr(settings, "debug") and not settings.debug):
            ttm_logger.debug("we are in debug but would normally talk to ISM here")
        else:
            ttm_logger.debug( "entering ISM code")
            event = TTM_Event(settings.mq_user,settings.mq_password,settings.mq_host,settings.mq_port, ssl_options=settings.mq_ssl_options,ssl=settings.mq_ssl)
            ttm_logger.debug( "event worked")
            ism_metric = {'event_type': 'compute.instance.bootstrap.end','eventType': 'Provisioning','payload': {'instance_id':metric['instance_id'] },'taskStartTime': metric['start_time'], 'taskEndTime':metric['end_time']}
            ttm_logger.debug("Sending event to ISM")
            ttm_logger.debug(ism_metric)
            event.send_event(json.dumps(ism_metric))
            ttm_logger.debug("ISM code End")

        r_server.hmset(metric_id, metric)

    except Exception as e:
        ttm_logger.exception("Exception occured in update metric")
        raise

    return jsonify( { 'metric': metric } ), 201

@app.route('/ttm/api/v1.0/instances/<string:instance_id>/recipe/<string:recipe_name>', methods=['POST'])
def update_recipe(instance_id, recipe_name):
    ttm_logger.debug('Entering update_recipe' )
    #This is called by utc_time
    metric = {} 
    try:
        if ( instance_id != None and instance_id.find('\"') != -1):
            instance_id = instance_id.replace('\"','')
        
        ttm_logger.debug('Instance Id: %s' % instance_id)
        ttm_logger.debug('recipe received: %s' % recipe_name)
        date = datetime.utcnow()
        metric_id_array = r_server.lrange(instance_id, 0, -1)
        if (metric_id_array):
            metric_id = metric_id_array[0]
            metric = r_server.hgetall(metric_id)

        if (metric):
            if (not metric.has_key("recipes")):
                metric["recipes"] = {}

            if(len(metric["recipes"]) > 0):
                import ast
                dict_recipes = ast.literal_eval(metric["recipes"])
                ttm_logger.debug("recipes exists in TTM")
                ttm_logger.debug("printing recipes dictionary: {0}".format(dict_recipes))

                if(dict_recipes.has_key(recipe_name)):
                    ttm_logger.debug("recipe {0} exists in recipes so updating endtime".format(recipe_name))
                    dict_recipes[recipe_name]["recipe_end_time"] = date.isoformat()
                    if (request.form.has_key("msg")):
                        dict_recipes[recipe_name]["end_msg"] = request.form["msg"]
                else:
                    ttm_logger.debug("Recipe {0} does not exists. Adding recipe".format(recipe_name))
                    dict_recipes[recipe_name] = {}
                    dict_recipes[recipe_name]["recipe_start_time"] = date.isoformat()
                    if (request.form.has_key("msg")):
                        dict_recipes[recipe_name]["start_msg"] = request.form["msg"]

                metric["recipes"] = dict_recipes
            else:
                ttm_logger.debug("No recipes exists. Adding recipes")
                metric["recipes"][recipe_name] = {}
                metric["recipes"][recipe_name]["recipe_start_time"] = date.isoformat()
                if (request.form.has_key("msg")):
                    metric["recipes"][recipe_name]["start_msg"] = request.form["msg"]

            r_server.hmset(metric_id, metric)
            ttm_logger.debug("update_recipe ends")
        else:
            ttm_logger.debug("a recipe {0} was provided but we don't have a a metric for instance_id {1}".format(recipe_name, instance_id))
    except Exception as e:
        ttm_logger.exception("Exception occured in update_recipe")

    return jsonify( { 'metric': metric } ), 201

@app.route('/ttm/api/v1.0/instances/<string:instance_id>/setmute', methods=['POST'])
def set_mute(instance_id):
    #get the instance from the redis db
    ttm_logger.debug("Entering set_mute")
    metric = {}
    try:
        if ( instance_id != None and instance_id.find('\"') != -1):
            instance_id = instance_id.replace('\"','')

        ttm_logger.debug('Instance Id: %s' % instance_id)
        metric_id_array = r_server.lrange(instance_id, 0, -1)
        if (not metric_id_array):
            ttm_logger.debug("set_mute: instance id does not exists in metrics so abort")
            abort(404)
        else:
            metric_id = metric_id_array[0]
            metric = r_server.hgetall(metric_id)
            ttm_logger.debug("Metric exists for {0}".format(instance_id))
            metric["mute"] = True
            ttm_logger.debug("Metric after updating mute flag to True is".format(metric))
            ttm_logger.debug("set_mute ends")
            r_server.hmset(metric_id, metric)

    except Exception as e:
        ttm_logger.exception("Exception occured in set_mute")

    return jsonify( { 'metric': metric } ), 201


@app.route('/ttm/api/v1.0/instances/nobootstrapstart/duration/<int:duration>', methods=['POST'])
def nobootstrapstart(duration):
    ttm_logger.debug("Entering nobootstrapstart")
    _instances = r_server.lrange('ttm_instance_ids', 0, -1)
    instances = []
    ttm_logger.debug("Going over all instances")

    for x in _instances:
        try:
            ttm_logger.debug("current instance id is {0}".format(x))
            current_time = datetime.utcnow()
            ttm_logger.debug("current_time is {0}".format(current_time))
            required_time = current_time - timedelta(minutes=duration)
            ttm_logger.debug("required_time is {0}".format(required_time))
            _metrics = r_server.lrange(x, 0, -1)
            for metric in _metrics:
                ttm_instance_start_time = r_server.hget(metric,'instance_start_time')
                ttm_logger.debug("instance_start_time is {0}".format(ttm_instance_start_time))
                ttm_mute_flag = r_server.hget(metric,'mute')
                ttm_logger.debug("mute flag for the instance is {0}".format(ttm_mute_flag))
                ttm_bootstrap_start_time = r_server.hget(metric,'bootstrap_start_time')
                ttm_logger.debug("bootstrap_start_time is {0}".format(ttm_bootstrap_start_time))
                instance_name = r_server.hget(metric,'instance_name')
                ttm_logger.debug("instance name is {0}".format(instance_name))
                if (ttm_instance_start_time):
                    str_ttm_instance_start_time = ttm_instance_start_time.split('.')
                    dt_ttm_instance_start_time = datetime.strptime(str_ttm_instance_start_time[0],"%Y-%m-%dT%H:%M:%S")
                    ttm_logger.debug("dt_ttm_instance_start_time is {0}".format(dt_ttm_instance_start_time))
                    if((dt_ttm_instance_start_time >= required_time) and
                            (ttm_mute_flag == 'False') and (ttm_bootstrap_start_time == "")):
                        instances.append(
                                {
                                    "instance_id": x
                                    ,"instance_name":instance_name
                                    ,"instance_start_time":ttm_instance_start_time
                                    ,"bootstrap_start_time":ttm_bootstrap_start_time
                                    ,"instance_ismute":ttm_mute_flag
                                    ,"current_time":current_time.isoformat()
                                }
                            )
        except Exception as e:
            ttm_logger.exception("Exception occured in nobootstrapstart")

    ttm_logger.debug("End of nobootstrapstart")
    return jsonify( { "instances": instances } )


@app.route('/ttm/api/v1.0/instances/nobootstrapend/duration/<int:duration>', methods=['POST'])
def nobootstrapend(duration):
    ttm_logger.debug("Entering nobootstrapend")
    _instances = r_server.lrange('ttm_instance_ids', 0, -1)
    instances = []

    for x in _instances:
        try:
            ttm_logger.debug("current instance id is {0}".format(x))
            current_time = datetime.utcnow()
            ttm_logger.debug("current_time is {0}".format(current_time))
            required_time = current_time - timedelta(minutes=duration)
            _metrics = r_server.lrange(x, 0, -1)
            for metric in _metrics:
                ttm_instance_start_time = r_server.hget(metric,'instance_start_time')
                ttm_logger.debug("instance_start_time is {0}".format(ttm_instance_start_time))
                ttm_mute_flag = r_server.hget(metric,'mute')
                ttm_logger.debug("mute flag for the instance is {0}".format(ttm_mute_flag))
                ttm_bootstrap_start_time = r_server.hget(metric,'bootstrap_start_time')
                ttm_logger.debug("bootstrap_start_time is {0}".format(ttm_bootstrap_start_time))
                ttm_bootstrap_end_time = r_server.hget(metric,'end_time')
                ttm_logger.debug("bootstrap_end_time is {0}".format(ttm_bootstrap_end_time))
                instance_name = r_server.hget(metric,'instance_name')
                ttm_logger.debug("instance name is {0}".format(instance_name))
                if (ttm_instance_start_time):
                    str_ttm_instance_start_time = ttm_instance_start_time.split('.')
                    dt_ttm_instance_start_time = datetime.strptime(str_ttm_instance_start_time[0],"%Y-%m-%dT%H:%M:%S")
                    ttm_logger.debug("dt_ttm_instance_start_time is {0}".format(dt_ttm_instance_start_time))
                    if((dt_ttm_instance_start_time >= required_time) and 
                            (ttm_mute_flag == 'False') and (ttm_bootstrap_end_time == "") and
                                   (ttm_bootstrap_start_time != "")):
                        instances.append(
                                {
                                    "instance_id": x
                                    ,"instance_name":instance_name
                                    ,"instance_start_time":ttm_instance_start_time
                                    ,"bootstrap_start_time":ttm_bootstrap_start_time
                                    ,"bootstrap_end_time":ttm_bootstrap_end_time
                                    ,"instance_ismute":ttm_mute_flag
                                    ,"current_time":current_time.isoformat()
                                }
                            )
        except Exception as e:
            ttm_logger.exception("Exception occured in nobootstrapend")

    ttm_logger.debug("End of nobootstrapend")
    return jsonify( { "instances": instances } )


if __name__ == '__main__':

    LOG_FILENAME = '/var/log/ttm/_ttm.log'
    ttm_logger = logging.getLogger('TTMLogger')
    ttm_logger.setLevel(logging.DEBUG)

    handler = RotatingFileHandler(LOG_FILENAME, maxBytes=100000000, backupCount=4)

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
       http_server.listen(5082, "localhost")
       IOLoop.instance().start()

    #uncomment the next 3 lines to use tornando to serve 



