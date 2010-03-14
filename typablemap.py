#!/usr/bin/env python
# -*- encoding: utf-8 -*-
from System.Text import Encoding
from System.IO import StringReader
from Misuzilla.Applications.TwitterIrcGateway import NilClasses, Status, Statuses, User, Users
from Misuzilla.Applications.TwitterIrcGateway.AddIns import TypableMapSupport
from Misuzilla.Applications.TwitterIrcGateway.AddIns.DLRIntegration import DLRIntegrationAddIn

class TypableMapManager(object):
	def __init__(self):
		CurrentSession.AddInManager.GetAddIn[DLRIntegrationAddIn]().BeforeUnload += self.on_before_unload
		self.typablemap_commands = CurrentSession.AddInManager.GetAddIn[TypableMapSupport]().TypableMapCommands
		self.registered_commands = []
		self.register_methods()
	
	def on_before_unload(self, sender, e):
		for command in self.registered_commands:
			self.typablemap_commands.RemoveCommand(command)
		self.registered_commands = []

	def register(self, command, desc, proc):
		self.registered_commands.append(command)
		self.typablemap_commands.AddCommand(command, desc, proc)
	
	def send_notice(self, msg, content):
		CurrentSession.SendChannelMessage(msg.Receiver, CurrentSession.CurrentNick, content, True, False, False, True)

	def execute_request_status(self, msg, url, data = ''):
		self.send_notice(msg, 'request: %s?%s' % (url, data))
		body = CurrentSession.TwitterService.POST(url, Encoding.UTF8.GetBytes(data))
		self.send_notice(msg, 'end request')
		if NilClasses.CanDeserialize(body):
			return None
		else:
			return Status.Serializer.Deserialize(StringReader(body))

	def register_methods(self):
		def retweet(p, msg, status, args):
			def f():
				retweeted = self.execute_request_status(msg, '/statuses/retweet/%s.xml' % status.Id)
				self.send_notice(msg, 'ユーザ %s のステータス "%s" を Retweet しました。' % (retweeted.User.ScreenName, retweeted.Text))
			p.Session.RunCheck(f)
			return True

		self.register("rt", "Retweet Command", retweet)

manager = TypableMapManager()

