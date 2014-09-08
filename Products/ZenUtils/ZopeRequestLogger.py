
import logging, logging.handlers 
import re
import os

class ZopeRequestLogger(object):
    """
    Logs information about the requests proccessed by Zopes.
    Disabled by default. It is enabled only when the file /opt/zenoss/etc/LOG_ZOPE_REQUESTS exists.
    """

    SEPARATOR = '@$@'
    FIELDS = []
    FIELDS.append('trace_type')
    FIELDS.append('start_time')
    FIELDS.append('server_name')
    FIELDS.append('server_port')
    FIELDS.append('path_info')
    FIELDS.append('action_and_method')
    FIELDS.append('client')
    FIELDS.append('http_host')
    FIELDS.append('http_method')
    FIELDS.append('XFF')

    ACTION_REGEX = '"action":"(.+?)"'
    METHOD_REGEX = '"method":"(.+?)"'

    ZENHOME = os.environ.get('ZENHOME')
    CONFIG_FILE = os.path.join(ZENHOME, 'etc', 'LOG_ZOPE_REQUESTS')
    DEFAULT_LOG_FILE = os.path.join(ZENHOME, 'log', 'ZReq.log')

    def __init__(self, filename = DEFAULT_LOG_FILE):
        self._log = None
        if os.path.isfile(ZopeRequestLogger.CONFIG_FILE):
            self._log = logging.getLogger('zope_request_logger')
            self._log.propagate = False
            handler = logging.handlers.RotatingFileHandler(filename, mode='a', maxBytes=10*1024*1024, backupCount=5)
            handler.setFormatter(logging.Formatter("%(asctime)s{0}%(message)s".format(ZopeRequestLogger.SEPARATOR)))
            self._log.addHandler(handler)
    
    def _extract_action_and_method_from_body(self, body):
        my_regex = re.compile(ZopeRequestLogger.ACTION_REGEX)
        actions = my_regex.findall(body)
        my_regex = re.compile(ZopeRequestLogger.METHOD_REGEX)
        methods = my_regex.findall(body)
        data = []
        for action, method in zip(actions, methods):
            data.append('({0},{1})'.format(action, method))
        return ''.join(data)

    def get_data_to_log(self, request, start_time):
        '''
        return a dict containing the request data that is relevant for logging purposes
        '''
        if self._log is None:
            return {}

        start_time = str(start_time)
        data = {}
        data['http_host'] = request.get('HTTP_HOST', default='')
        data['server_name'] = request.get('SERVER_NAME', default='')
        data['server_port'] = request.get('SERVER_PORT', default='')
        data['path_info'] = request.get('PATH_INFO', default='')
        data['action_and_method'] = ''
        if request.get('BODY'):
            data['action_and_method'] = self._extract_action_and_method_from_body(request.get('BODY'))
        data['client'] = request.get('REMOTE_ADDR', default='')
        data['start_time'] = start_time
        data['http_method'] = request.get('method', default='')
        data['XFF'] = request.get('X_FORWARDED_FOR', default='')
        return data

    def log_request(self, data_to_log, finished=False):
        ''' '''
        if self._log:
            if finished:
                data_to_log['trace_type'] = 'END'
            else:
                data_to_log['trace_type'] = 'START'

            trace = []
            for field in ZopeRequestLogger.FIELDS:
                trace.append(data_to_log.get(field, ''))
        
            self._log.info((ZopeRequestLogger.SEPARATOR).join(trace))

