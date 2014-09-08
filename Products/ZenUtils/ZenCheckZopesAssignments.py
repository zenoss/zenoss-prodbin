##############################################################################
# 
# Copyright (C) Zenoss, Inc. 2014, all rights reserved.
# 
# This content is made available according to terms specified in
# License.zenoss under the directory where your Zenoss product is installed.
# 
##############################################################################

from ZopeRequestLogger import ZopeRequestLogger

import subprocess
import re
import time
import datetime
import os
import sys

import argparse

SCRIPT_VERSION = '1.0.0'

def execute_command(command):
    """
    Params: command to execute
    Return: tuple containing the stout and stderr of the command execution
    """
    proc = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    stdout, stderr = proc.communicate()
    return (stdout, stderr)

class ZopeInfoRetriever(object):

	COMMAND = "zenwebserver status -v"
	STATUS_REGEX = '(?P<name>.*) status (\s+)\[(?P<status>.+)\]'
	PID_PORT_REGEX = 'Running \(pid (?P<pid>\d+)\), Listening \(port (?P<port>.*)\)'
	def __init__(self):
		pass

	def _execute_regex(self, expr, line):
		results = {}
		regex = re.compile(expr)
		match = regex.search(line)
		if match:
			results = match.groupdict()
		return results

	def _match_status_line(self, line):
		return self._execute_regex(ZopeInfoRetriever.STATUS_REGEX, line)

	def _match_pid_line(self, line):
		return self._execute_regex(ZopeInfoRetriever.PID_PORT_REGEX, line)

	def _parse_command_output(self, output):
		zopes = []
		zope = None
		for line in output.split('\n'):
			status_line_results = self._match_status_line(line)
			if status_line_results:
				zope = ZopeInfo()
				zope.name = status_line_results.get('name', '')
				zope.status = status_line_results.get('status', '')
				if 'UP' in zope.status:
					zope.running = True
				else:
					zopes.append(zope)
					zope = None
			else:
				pid_line_results = self._match_pid_line(line)
				if pid_line_results:
					zope.pid = pid_line_results.get('pid', '')
					zope.port = pid_line_results.get('port', '')
					zope.id = zope.port
					zopes.append(zope)
		return zopes

	def getZopesInfo(self):
		""" """
		zopes = []
		output, stderr = execute_command(ZopeInfoRetriever.COMMAND)
		if len(stderr) > 0:
			print 'error'
		else:
			zopes = self._parse_command_output(output)
		return zopes

class ProcessInfoRetriever(object):

	COMMAND = 'ps -p {0} -o %cpu,%mem,etime,cmd | tail -n +2'

	def __init__(self):
		pass

	def _parse_elapsed_time(self, etime):
		'''
		etime format: days-HH:MM:SS
		'''
		if not etime:
			return ''

		parsing = etime.split('-')
		days = ''
		if len(parsing) > 1:
			days = parsing[0]
			remaining = parsing[1]
		else:
			remaining = parsing[0]

		time = remaining.split(':')
		time = time[::-1]
		seconds = 0
		if days:
			seconds = 24 * 60 * 60
		for index, element in enumerate(time):
			seconds = seconds + pow(60, index)*int(element)
		return seconds


	def get_process_info(self, pid):
		info = {}
		command = ProcessInfoRetriever.COMMAND.format(pid)
		output, stderr = execute_command(command)
		if len(stderr) == 0 and len(output) > 0:
			data = output.split()
			if len(data) >= 3:
				info['pid'] = pid
				info['cpu'] = data[0]
				info['mem'] = data[1]
				#import pdb; pdb.set_trace()
				info['etime'] = data[2]
				info['seconds_running'] = self._parse_elapsed_time(data[2])
				info['cmd'] = ' '.join(data[3:])
		return info

class ZopeLogRetriever(object):

	SEPARATOR = ZopeRequestLogger.SEPARATOR

	FIELDS = ['log_timestamp'] + ZopeRequestLogger.FIELDS

	def __init__(self):
		pass

	def _parse_line(self, line):
		parsed_line = {}
		line = line.strip()
		data = line.split(ZopeLogRetriever.SEPARATOR)
		if len(data) > 0:
			parsed_line['fingerprint'] = (ZopeLogRetriever.SEPARATOR).join(data[2:])
			for field, value in zip(ZopeLogRetriever.FIELDS, data):
				parsed_line[field] = value
		return parsed_line

	def read_log(self, path):
		lines = []
		with open(path) as f:
			for line in f:
				parsed_line = self._parse_line(line)
				lines.append(parsed_line)
		return lines

#------------------------------------------------------------------------------------------------

class ZopeInfo(object):

	def __init__(self):
		self.id = ''
		self.name = ''
		self.pid = ''
		self.status = ''
		self.running = False
		self.port = ''
		#Zope process info
		self.cpu = '-1'
		self.mem = '-1'
		self.cmd = ''
		self.etime = ''
		self.seconds_running = 0
		#Zope Assigments
		self.assignments = {}

	def add_assignment(self, assignment):
		if 'START' in assignment.trace_type:
			self.assignments[assignment.fingerprint] = assignment
		elif 'END' in assignment.trace_type and assignment.fingerprint in self.assignments.keys():
			del self.assignments[assignment.fingerprint]

	def set_process_info(self, data):
		self.cpu = data.get('cpu', '')
		self.mem = data.get('mem', '')
		self.etime = data.get('etime', 0)
		self.seconds_running = data.get('seconds_running', 0)
		self.cmd = data.get('cmd', '')

	def __str__(self):
		if self.running:
			return 'Zope: port [{0}] / pid [{1}] / %cpu [{2}] / %mem [{3}] / etime [{4}]'.format(self.port, self.pid, self.cpu, self.mem, self.etime)
		else:
			return 'Zope: port [{0}]'.format(self.port)

class ZopeAssignment(object):

	def __init__(self, data):
		self.log_timestamp = data.get('log_timestamp', '')
		self.fingerprint = data.get('fingerprint', '')
		self.trace_type = data.get('trace_type', '')
		self.start_time = data.get('start_time', '')
		self.server_name = data.get('server_name', '')
		self.server_port = data.get('server_port', '')
		self.path_info = data.get('path_info', '')
		self.http_method = data.get('http_method', '')
		self.client = data.get('client', '')
		self.http_host = data.get('http_host', '')
		self.action_and_method = data.get('action_and_method', '')
		self.forwarded_for = data.get('XFF', '')
		self.zope_id = self.server_port

	def __str__(self):
		t = datetime.datetime.fromtimestamp(float(self.start_time))
		now = datetime.datetime.now()
		format = "%Y-%m-%d %H:%M:%S"
		running_since = t.strftime(format)
		ass_str = [ 'Request started {0}. ({1} seconds ago)'.format(running_since, str(datetime.datetime.now() - t)) ]
		ass_str.append('Client: {0}'.format(self.client))
		ass_str.append('HTTP Method: {0}'.format(self.http_method))
		ass_str.append('Path: {0}'.format(self.path_info))
		ass_str.append('Action/Method: {0}'.format(self.action_and_method))
		if self.forwarded_for:
			ass_str.append('Forwarded for: {0}'.format(self.forwarded_for))
		return '\n\t\t'.join(ass_str)

class ZopesManager(object):

	def __init__(self):
		self.zopes = {} # dict {zope_id: ZopeInfo}

	def _load_zopes_assignments(self, path_to_log):
		'''
		return a dict zope_id : assignments found for zope_id
		'''
		log_retreiver = ZopeLogRetriever()
		parsed_lines = log_retreiver.read_log(path_to_log)
		assignments = {}
		for data in parsed_lines:
			new_assignment = ZopeAssignment(data)
			zope_assignments = assignments.get(new_assignment.zope_id, [])
			zope_assignments.append(new_assignment)
			assignments[new_assignment.zope_id] = zope_assignments
		return assignments

	def _get_running_zopes(self):
		''' Loads available zopes by executing zenwebserver status -v '''
		running_zopes = {}

		zope_retriever = ZopeInfoRetriever()
		zope_list = zope_retriever.getZopesInfo()
		process_info_retreiver = ProcessInfoRetriever()
		for zope in zope_list:
			if zope.id and 'Load balancer' not in zope.name and zope.running:
				process_info = process_info_retreiver.get_process_info(zope.pid)
				zope.set_process_info(process_info)
				running_zopes[zope.id] = zope
		return running_zopes

	def _get_zope_for_assignment(self, assignment):
		assignment_for = None
		for zope_id in self.zopes.keys():
			zope = self.zopes.get(zope_id)
			if zope and assignment.zope_id in zope_id:
				assignment_for = zope
				break
		return assignment_for

	def _process_assigments(self, assigments, process_all=True):
		'''
		all = True  : all assigments are processed
		all = False : only assignments processed by a zope that is 
		              running and assignment.start_time > zope.start_time
		'''
		for zope_id, assignments in assigments.iteritems():
			if not zope_id: continue
			for assignment in assignments:
				if process_all:
					if zope_id not in self.zopes.keys():
						zope = ZopeInfo()
						zope.zope_id = zope_id
						zope.port = assignment.server_port
						self.zopes[zope_id] = zope
					self.zopes[zope_id].add_assignment(assignment)
				else:
					zope = self._get_zope_for_assignment(assignment)
					if zope and zope.seconds_running > 0:
						now_timestamp = datetime.datetime.now()
						ass_timestamp = datetime.datetime.fromtimestamp(float(assignment.start_time))
						assignment_running_for = (now_timestamp - ass_timestamp).total_seconds()
						if assignment_running_for > 5  and assignment_running_for < float(zope.seconds_running):
							zope.add_assignment(assignment)

	def print_zopes_stats(self):
		os.system('clear')
		print '\n\n\n'
		line_offset = 50
		if len(self.zopes.keys()) == 0:
			print '%' * line_offset
			print 'NO ZOPES FOUND!!'.center(line_offset)
			print '%' * line_offset

		for zope_id in sorted(self.zopes.keys()):
			zope = self.zopes.get(zope_id)
			zope_str = str(zope)
			l = len(zope_str) + line_offset
			print '\n\n'
			print '=' * l 
			print '{0}'.format(zope_str.center(l))
			print '=' * l
			if len(zope.assignments.keys()) == 0:
				print 'No unfinished assignments.'.center(l)
			else:
				print 'Unfinished assignments found:'
			first = True
			for fingerprint, assignment in zope.assignments.iteritems():
				if first:
					first = False
				else:
					print '-' * l
				print '      {0}'.format(assignment)
			print '=' * l

	def check_running_zopes_assignments(self, fname):
		self.zopes = {}
		assignments = self._load_zopes_assignments(fname)
		self.zopes = self._get_running_zopes()
		self._process_assigments(assignments, process_all=False)
		self.print_zopes_stats()

	def check_all_zopes_assignments(self, fname):
		self.zopes = {} # Zopes will be populated when assignments are processed
		assignments = self._load_zopes_assignments(fname)
		self._process_assigments(assignments, process_all=True)
		self.print_zopes_stats()

def parse_options():
    """Defines command-line options for script """
    parser = argparse.ArgumentParser(version=SCRIPT_VERSION,
                                     description="Checks for unfinished Zope requests.")
    parser.add_argument("-f", "--file", action="store", default=ZopeRequestLogger.DEFAULT_LOG_FILE,
                        help="path to Zope's assignments log file")
    parser.add_argument("-r", "--running_zopes", action="store_true", default=False,
                        help="Displays non finished requests for zopes that are currently running")
    parser.add_argument("-c", "--cycle", action="store_true", default=False,
                        help="performs the check periodically and only checks for requests assigned to zopes that are currently running")
    parser.add_argument("-freq", "--freq", action="store", default=5, type=int,
                        help="frecuency at which the check is performed (in seconds)")
    return vars(parser.parse_args())

def main():
	""" """
	cli_options = parse_options()
	fname = cli_options.get('file')
	if os.path.isfile(fname):
		os.system('clear')
		while True:
			zopes_manager = ZopesManager()
			if cli_options.get('running_zopes'):
				zopes_manager.check_running_zopes_assignments(fname)
			else:
				zopes_manager.check_all_zopes_assignments(fname)
			if not cli_options.get('cycle'):
				break;
			print '\n\n'
			print '-' * 100
			print ('SLEEPING for {0} seconds'.format(cli_options.get('freq'))).center(100)
			print '-' * 100
			print '\n\n'
			time.sleep(cli_options.get('freq'))
	else:
		print "ERROR: Can't open file {0}".format(fname)
		sys.exit(1)

if __name__ == "__main__":
	main()


