# -*- coding: utf-8 -*-
import sys
import os
import codecs
import BaseHTTPServer
import time
import json
import random
import string
import cgi
import re
import urllib
import Skype4Py
from bs4 import BeautifulSoup
from ConfigParser import SafeConfigParser

URL_PTN = r'(https?://\S+)'
URL_PTN2 = r"(?i)\b((?:https?://|www\d{0,3}[.]|[a-z0-9.\-]+[.][a-z]{2,4}/)(?:[^\s()<>]+|\(([^\s()<>]+|(\([^\s()<>]+\)))*\))+(?:\(([^\s()<>]+|(\([^\s()<>]+\)))*\)|[^\s`!()\[\]{};:'\".,<>?«»“”‘’]))"

def logger(content, show = True):
	logfile = codecs.open("log.txt", mode="a", encoding="utf-8")
	content = str(time.asctime()) + ": " + content
	logfile.write(content)
	logfile.write("\n")
	logfile.flush()
	if show:
		print content.encode('cp950', errors='replace') # cp950 for chinese windows cmd console

parser = SafeConfigParser()
with codecs.open('config.ini', 'r', encoding='utf-8') as f:
    parser.readfp(f)
HOST_NAME = parser.get('aniarc-skype-bot', 'hostname')
PORT_NUMBER = int(parser.get('aniarc-skype-bot', 'port'))
CHAT_TOPIC = parser.get('aniarc-skype-bot', 'topic')
logger('Config: config.ini read okay')

def AttachmentStatusText(status):
   return skype.Convert.AttachmentStatusToText(status)

def OnAttach(status):
    logger('Skyper: API Attachment ' + AttachmentStatusText(status))
    if status == Skype4Py.apiAttachAvailable:
        skype.Attach()

def skypeMessageStatus(msg, Status):
	if Status == 'RECEIVED':
		m = exec(msg)
		m = re.findall(URL_PTN, msg.Body)
		if m:
			logger("Parser: %s says url: %s" % ( str(msg.FromHandle), str(m[0])) )
			t1 = time.time()
			title = BeautifulSoup(urllib.urlopen(m[0])).title.string
			t2 = time.time()
			msg.Chat.SendMessage(title)
			logger("Parser: in %s we got title:" % str(t2 - t1) )
			logger(title)
		msg.MarkAsSeen()

skype = Skype4Py.Skype()
skype.OnAttachmentStatus = OnAttach
logger('Skyper: Connecting...')
skype.Attach()
logger('Logger: Appending...')
skype.OnMessageStatus =	skypeMessageStatus
logger('Parser: Watching URLs...')

def skypeSendBitbucket(msg, payload):
	good = random.choice(['nice work!', 'good job!', 'well done!', 'sounds great!', 'how lovely!', 'thank you!', 'wonderful!', 'tremendous!', 'keep going!', 'you made it!'])
	for chat in skype.Chats:
		if(CHAT_TOPIC in chat.Topic):
			output = 'bitbucket: '
			for c in msg['commits']:
				output += str(c['author']) + ' commits to ' + str(msg['repository']['name']) + ' / ' + str(c['branch']) + ' : ' + '\n'
				output += str(c['message']) + '\n'
			if (payload.find('db/migrate')>0):
				output += 'db schema changed, please rake db:migrate !' + '\n'
			if (payload.find('Gemfile')>0):
				output += 'Gemfile changed, please bundle install!' + '\n'
			chat.SendMessage(output)

def skypeSendGithub(msg, payload):
	output = ''
	if (payload.find('closed_at')>0): # issue
		output += msg['issue']['user']['login'] + ' has ' + msg['status'] + ' issue #' + msg['issue']['number'] + ' assigned to ' + msg['issue']['assignee']['login']
		output += msg['issue']['title'] + '\n'
		output += msg['issue']['url'] + '\n'
	else:
		output += str(msg['head_commit']['author']['name']) + ' commits to ' + str(msg['repository']['name']) + ' / ' + str(msg['ref'].replace('refs/heads/','')) + ' (github): ' + '\n'
		output += str(msg['head_commit']['message']) + '\n'
		if (payload.find('db/migrate')>0):
			output += 'db schema changed, please rake db:migrate !' + '\n'
		if (payload.find('Gemfile')>0):
			output += 'Gemfile changed, please bundle install!' + '\n'
		if (msg["forced"] == "true"):
			output += 'warning, FORCED UPDATE!' + '\n'
		output += msg['compare'] + '\n'
		i = 0
		for c in msg['commits']:
			i = i+1
			if (i >= len(msg['commits'])):
				continue
			else:
				output += str(c['author']['name']) + ': ' + str(c['message']) + '\n'

	for chat in skype.Chats:
		if(CHAT_TOPIC in chat.Topic):
			chat.SendMessage(output)

def skypeSendErrbit(param, errbit_url):
	notify_when_times = [2, 3, 7, 15, 25, 50, 100]
	output = ''
	for chat in skype.Chats:
		if((CHAT_TOPIC in chat.Topic) and (str(param['app_name']).find('-prod')>0)):
			if main.last_error == param['where']:
				main.last_error_count = main.last_error_count + 1
				if main.last_error_count in notify_when_times:
					output = 'Last error occured ' + str(main.last_error_count) + ' times!'
					chat.SendMessage(output)
					return
			else:
				main.last_error = param['where']
				main.last_error_count = 0
				output += str(param['app_name']) + ' (' + str(param['hosts'].itervalues().next()['value']) + ') error on ' + str(param['where']) + '.\n'
				output += str(errbit_url) + '\n'
				output += str(param['message']) + '\n'
				chat.SendMessage(output)

def skypeSendUservoice(event, msg):
	for chat in skype.Chats:
		if(CHAT_TOPIC in chat.Topic):
			output = 'uservoice: '
			output += str(event) + '\n'
			output += str(msg) + '\n'
			chat.SendMessage(output)

class REST(BaseHTTPServer.BaseHTTPRequestHandler):

	def do_GET(self):	
		self.wfile.write('Do you yahoo?')	

	def do_POST(self):
		self.wfile.write('Do you yahoo?')
		post_body = self.rfile.read(int(self.headers.getheader('content-length')))
		logger("Server: POST from client: " + self.client_address[0])
		logger("Server: POST content: " + post_body, False)

		if (post_body.find('canon_url')>0):
			payload = '{' + urllib.unquote(post_body).replace('+',' ')[9:-1] + '}'
			msg = json.loads(payload)
			skypeSendBitbucket(msg, payload)
			logger("BitBucket: %s commits to %s/%s" % ( str(msg['commits'][0]['author']), str(msg['repository']['name']), str(msg['commits'][0]['branch']) ) )

		elif (urllib.unquote(post_body).find('//github.com')>0):
			payload = '{' + urllib.unquote(post_body)[9:-1] + '}'
			msg = json.loads(payload)
			skypeSendGithub(msg, payload)
			logger("Github: %s commits to %s/%s %s" % ( str(msg['head_commit']['author']['name']), str(msg['repository']['name']), str(msg['ref'].replace('refs/heads/','')), ("true" if str(msg['forced']) == "true" else "") ) )

		elif (urllib.unquote(post_body).find('signature=')>0):
			param = cgi.parse_qs(post_body)
			msg = json.loads(param['data'][0])
			skypeSendUservoice(str(param['event'][0]), msg)
			logger("Uservoice: %s %s" % (str(param['event'][0]), str(msg)) )

		else:
			param = cgi.parse_qs(post_body)
			msg = json.loads(param['problem'][0])
			skypeSendErrbit(msg, param['errbit_url'][0])
			logger("Errbit: %s error on %s" % ( str(msg['app_name']), str(msg['where']) ) )

def main(server_class=BaseHTTPServer.HTTPServer, handler_class=REST):

	httpd = server_class((HOST_NAME, PORT_NUMBER), REST)
	logger( "Server: Starts Listening %s:%s" % (HOST_NAME, PORT_NUMBER) )
	main.last_error = ''
	main.last_error_count = 0
	try:
		httpd.serve_forever()
	except KeyboardInterrupt:
		pass
	httpd.server_close()
	logger( "Server: Stop Listening %s:%s" % (HOST_NAME, PORT_NUMBER) )
	logger( "Logger: Close" )

if __name__ == '__main__':
	main()
