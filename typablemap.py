#!/usr/bin/env python
# -*- encoding: utf-8 -*-
import sys
import re
from System import String
from System.Text import Encoding
from System.IO import StringReader
from System.Net import WebClient, WebException
from Misuzilla.Applications.TwitterIrcGateway import NilClasses, Status, Statuses, User, Users
from Misuzilla.Applications.TwitterIrcGateway.AddIns import TypableMapSupport
from Misuzilla.Applications.TwitterIrcGateway.AddIns.DLRIntegration import DLRIntegrationAddIn

class TypableMap(object):
	@classmethod
	def instance(cls):
		if not hasattr(cls, '__instance__'):
			cls.__instance__ = TypableMap()
		return cls.__instance__

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
	
	def apply_typablemap(self, status):
		if CurrentSession.Config.EnableTypableMap:
			id = self.typablemap_commands.TypableMap.Add(status)
			if CurrentSession.Config.TypableMapKeyColorNumber < 0:
				status.Text = '%s (%s)' % (status.Text, id)
			else:
				status.Text = '%s %c%s(%s)' % (status.Text, chr(0x03), CurrentSession.Config.TypableMapKeyColorNumber, id)

		return status

	@classmethod
	def send_notice(cls, receiver, nick, content):
		CurrentSession.SendChannelMessage(receiver, nick, content, True, False, False, True)

	@classmethod
	def run_check(cls, msg, command, error):
		try:
			return CurrentSession.RunCheck(command, error)
		except:
			(type, value, traceback) = sys.exc_info()
			cls.send_notice(msg.Receiver, CurrentSession.CurrentNick, str(type))
			cls.send_notice(msg.Receiver, CurrentSession.CurrentNick, str(value))
			return False

	@classmethod
	def post(cls, url, data=''):
		return CurrentSession.TwitterService.POST(url, Encoding.UTF8.GetBytes(data))

	@classmethod
	def get(cls, url):
		return CurrentSession.TwitterService.GET(url)

	@classmethod
	def deserialize(cls, type, xml):
		if NilClasses.CanDeserialize(xml):
			return None
		else:
			return type.Serializer.Deserialize(StringReader(xml))

	def register_methods(self):
		# 公式 RT する
		def retweet(p, msg, status, args):
			def command():
				retweeted = self.deserialize(Status, self.post('/statuses/retweet/%s.xml' % status.Id))
				retweeted = self.apply_typablemap(retweeted)
				self.send_notice(msg.Receiver, CurrentSession.CurrentNick, 'ユーザ %s のステータス "%s" を Retweet しました。' % (status.User.ScreenName, retweeted.Text))

			def error():
				self.send_notice(msg.Receiver, CurrentSession.CurrentNick, 'エラー: Retweet に失敗しました。')

			self.run_check(msg, command, error)
			return True

		# search.twitter.com の Show Conversation を表示する
		def show_conversation(p, msg, status, args):
			def command():
				empty = False
				try:
					body = WebClient().DownloadString('http://search.twitter.com/search/thread/%s' % status.Id)
					divs = re.findall(r'<div class="msg">(.*?)</div>', body, re.S)
					if len(divs) > 0:
						for div in divs:
							match = re.search(r'<a[^>]*>(.*?)</a>.*<span[^>]*>(.*?)</span>', div)
							name = match.group(1)
							text = re.sub(r'<[^>]*>', '', match.group(2))
							self.send_notice(msg.Receiver, name, text)
					else:
						empty = True
				except:
					# 404とかなんだけどなにでキャッチすればいいのか
					empty = True
				finally:
					if empty:
						self.send_notice(msg.Receiver, CurrentSession.CurrentNick, 'エラー: 会話が存在しません。')

			def error():
				self.send_notice(msg.Receiver, CurrentSession.CurrentNick, 'エラー: 会話の取得に失敗しました。')

			self.run_check(msg, command, error)
			return True

		# 返信を表示する
		def show_reply_to_status(recursive=False):
			def inner(p, msg, _status, args):
				def command():
					def has_reply_to_status_id(s):
						return s.InReplyToStatusId != None and len(s.InReplyToStatusId) > 0

					status = _status
					if not has_reply_to_status_id(status):
						self.send_notice(msg.Receiver, CurrentSession.CurrentNick, 'エラー: 返信先のステータスが存在しません。')
					else:
						statuses = []
						try:
							while True:
								reply_to_status = self.deserialize(Status, self.get('/statuses/show/%s.xml' % status.InReplyToStatusId))
								reply_to_status = self.apply_typablemap(reply_to_status)
								statuses.append(reply_to_status)
								if not recursive or not has_reply_to_status_id(reply_to_status):
									break
								else:
									status = reply_to_status
						finally:
							# 逆順で流す
							statuses.reverse()
							for s in statuses:
								self.send_notice(msg.Receiver, s.User.ScreenName, s.Text)

				def error():
					self.send_notice(msg.Receiver, CurrentSession.CurrentNick, 'エラー: 返信先のステータスの取得に失敗しました。')

				self.run_check(msg, command, error)
				return True

			return inner

		# タイムラインを表示する
		def show_timeline(p, msg, status, args):
			def command():
				count = 5 if String.IsNullOrEmpty(args) else int(args)
				statuses = self.deserialize(Statuses, self.get('/statuses/user_timeline.xml?user_id=%s&max_id=%s&count=%s' % (status.User.Id, status.Id, count)))
				statuses = list(statuses.Status)

				statuses.reverse()
				for s in statuses:
					s = self.apply_typablemap(s)
					self.send_notice(msg.Receiver, s.User.ScreenName, s.Text)

			def error():
				self.send_notice(msg.Receiver, CurrentSession.CurrentNick, 'エラー: タイムラインの取得に失敗しました。')

			self.run_check(msg, command, error)
			return True

		# register typablemap commands
		self.register('rt', 'Retweet command', retweet)
		self.register('cv', 'Show conversation command', show_conversation)
		self.register('res', 'Show reply to status command', show_reply_to_status())
		self.register('rres', 'Show recursive reply to status command', show_reply_to_status(True))
		self.register('tl', 'Show timeline command', show_timeline)

# instanciate
typablemap = TypableMap.instance()
