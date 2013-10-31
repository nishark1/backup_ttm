import pika
 
class TTM_Event:
    def __init__(self, user, password, host, port, ssl_options=None, ssl=False):
        self.credentials = pika.PlainCredentials(user, password)
        self.parameters = pika.ConnectionParameters(host, port, '/', self.credentials, ssl_options=ssl_options, ssl=ssl)
        self.connection = self._connection(self.parameters)
 
    def _connection(self, parameters):
        try:
            connection =  pika.BlockingConnection(parameters)
            print "connection worked"
            return connection
        except:
            print "Connection to RabbitMQ Failed!!!"
 

    def send_event(self, body):
        if self.connection.is_open:
            try:
                channel = self.connection.channel()
                channel.exchange_declare(exchange='nova', type='topic')
                #send the body with double quotes outside
                channel.basic_publish(exchange='nova', routing_key='ismp_topic.info', body=body)
                print "Successfully published!!!"
            except:
                print "TTM Event was not published to Nova exchange!!!"
        else:
            # add code to restablish connection
            print "Connection to RabbitMQ is Closed!!!"

      
