# -*- coding: utf-8 -*-

import Skype4Py
import json
import BaseHTTPServer
import time
import urllib
import random
import string
import cgi
from ConfigParser import SafeConfigParser
import codecs

def logger(content, show = True):
	logfile = open("log.txt", "a")
	content = str(time.asctime()) + ": " + content
	logfile.write(content + "\n")
	logfile.flush()
	if show:
		print content

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

skype = Skype4Py.Skype()
skype.OnAttachmentStatus = OnAttach
logger('Skyper: Connecting...')
skype.Attach()
logger('Logger: Appending...')


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

def skypeSendErrbit(param):
	for chat in skype.Chats:
		if((CHAT_TOPIC in chat.Topic) and (str(param['app'])[2:-2].find('-prod')>0)):
			output  = str(param['app'])[2:-2] + ' (' + str(param['hostname'])[2:-2] + ') error on ' + str(param['where'])[2:-2] + '.\n'
			output += str(param['url'])[2:-2] + '\n'
			output += str(param['msg'])[2:-2] + '\n'
			output += str(param['errbit_url'])[2:-2] + '\n'
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

		else:
			param = cgi.parse_qs(post_body)
			skypeSendErrbit(param)
			logger("Errbit: %s %s error on %s" % ( str(param['hostname'])[2:-2], str(param['app'])[2:-2], str(param['where'])[2:-2] ) )

def main(server_class=BaseHTTPServer.HTTPServer, handler_class=REST):

	httpd = server_class((HOST_NAME, PORT_NUMBER), REST)
	logger( "Server: Starts Listening %s:%s" % (HOST_NAME, PORT_NUMBER) )
	try:
		httpd.serve_forever()
	except KeyboardInterrupt:
		pass
	httpd.server_close()
	logger( "Server: Stop Listening %s:%s" % (HOST_NAME, PORT_NUMBER) )
	logger( "Logger: Close" )

if __name__ == '__main__':
	main()
