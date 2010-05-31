#!/usr/bin/env python
# -*- encoding: utf-8 -*-
import sys
import re
from System import String
from System.Text import Encoding
from System.IO import StringReader
from System.Net import WebClient, WebException
from Misuzilla.Applications.TwitterIrcGateway import NilClasses, Status, Statuses, User, Users
from Misuzilla.Applications.TwitterIrcGateway.AddIns import TypableMapSupport, ShortenUrlService
from Misuzilla.Applications.TwitterIrcGateway.AddIns.DLRIntegration import DLRIntegrationAddIn

class TypableMapError(Exception):
	pass

class TypableMap(object):
	@classmethod
	def instance(cls):
		if not hasattr(cls, '__instance'):
			cls.__instance = TypableMap()
		return cls.__instance

	def __init__(self):
		CurrentSession.AddInManager.GetAddIn[DLRIntegrationAddIn]().BeforeUnload += self.on_before_unload
		self.typablemap_commands = CurrentSession.AddInManager.GetAddIn[TypableMapSupport]().TypableMapCommands
		self.shorten_url_service = CurrentSession.AddInManager.GetAddIn[ShortenUrlService]()
		self.registered_commands = []
		self.register_commands()

	def on_before_unload(self, sender, e):
		for command in self.registered_commands:
			self.typablemap_commands.RemoveCommand(command)
		self.registered_commands = []

	def register(self, command, desc, proc):
		self.registered_commands.append(command)
		self.typablemap_commands.AddCommand(command, desc, proc)
	
	def apply_typablemap(self, status, text=None):
		if text is None:
			text = status.Text

		if CurrentSession.Config.EnableTypableMap:
			cno = CurrentSession.Config.TypableMapKeyColorNumber
			id = self.typablemap_commands.TypableMap.Add(status)
			if cno < 0:
				text += ' (%s)' % (id)
			else:
				text += ' %c%d(%s)%c' % (chr(0x03), cno, id, chr(0x03))

		return text

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
		return CurrentSession.TwitterService.POST(url, data)

	@classmethod
	def get(cls, url):
		return CurrentSession.TwitterService.GET(url)

	@classmethod
	def deserialize(cls, type, xml):
		if NilClasses.CanDeserialize(xml):
			return None
		else:
			return type.Serializer.Deserialize(StringReader(xml))

	def register_commands(self):
		# 公式 RT する
		def retweet(p, msg, _status, args):
			def command():
				status = self.deserialize(Status, self.post('/statuses/retweet/%d.xml' % _status.Id))
				retweeted = status.RetweetedStatus
				text = self.apply_typablemap(status, text=retweeted.Text)
				self.send_notice(msg.Receiver, CurrentSession.CurrentNick, 'ユーザ %s のステータス "%s" を RT しました。' % (retweeted.User.ScreenName, text))

			def error(e):
				self.send_notice(msg.Receiver, CurrentSession.CurrentNick, 'エラー: RT に失敗しました。')
				self.send_notice(msg.Receiver, CurrentSession.CurrentNick, e.Message)

			self.run_check(msg, command, error)
			return True

		# 非公式 RT する
		def unofficial_retweet(p, msg, status, args):
			def command():
				comment = ''
				if args is not None and len(args) > 0:
					comment = '%s ' % args

				target = ''
				if True:
					target = '@%s ' % status.User.ScreenName

				url = 'http://twitter.com/%s/status/%s' % (status.User.ScreenName, status.Id)
				if self.shorten_url_service is not None:
					url = self.shorten_url_service.ShortenUrl(url, self.shorten_url_service.Timeout)

				update_text = '%sRT: %s%s' % (comment, target, url)
				update_status = CurrentSession.UpdateStatus(update_text)
				self.send_notice(msg.Receiver, CurrentSession.CurrentNick, update_text)
				CurrentSession.UpdateStatusWithReceiverDeferred(msg.Receiver, update_text)

			def error(e):
				self.send_notice(msg.Receiver, CurrentSession.CurrentNick, 'エラー: 非公式 RT に失敗しました。')
				self.send_notice(msg.Receiver, CurrentSession.CurrentNick, e.Message)

			self.run_check(msg, command, error)
			return True

		# search.twitter.com の Show Conversation を表示する
		def show_conversation(p, msg, status, args):
			def command():
				empty = False
				try:
					client = WebClient()
					client.Encoding = Encoding.UTF8
					client.Headers['Accept'] = 'text/html'
					client.Headers['User-Agent'] = 'Mozilla/4.0 (compatible; MSIE 8.0; Windows NT 6.1; Trident/4.0)'

					body = client.DownloadString('http://search.twitter.com/search/thread/%d' % status.Id)
					divs = re.findall(r'<div class="msg">(.*?)</div>', body, re.S)
					if len(divs) > 0:
						for div in divs:
							match = re.search(r'<a[^>]*>(.*?)</a>.*<span[^>]*>(.*?)</span>', div)
							name = match.group(1)
							text = re.sub(r'<[^>]*>', '', match.group(2))
							self.send_notice(msg.Receiver, name, text)
					else:
						empty = True
				except WebException, e:
					if e.Response.StatusCode == 404:
						# クロールされていないかプロテクトか
						empty = True
					else:
						raise
				finally:
					if empty:
						self.send_notice(msg.Receiver, CurrentSession.CurrentNick, 'エラー: 会話が存在しません。')

			def error(e):
				self.send_notice(msg.Receiver, CurrentSession.CurrentNick, 'エラー: 会話の取得に失敗しました。')
				self.send_notice(msg.Receiver, CurrentSession.CurrentNick, e.Message)

			self.run_check(msg, command, error)
			return True

		# 返信を表示する
		def show_reply_to_status(recursive=False):
			def inner(p, msg, _status, args):
				def command():
					def has_reply_to_status_id(s):
						id = s.InReplyToStatusId
						return id is not None and len(id) > 0

					status = _status
					if not has_reply_to_status_id(status):
						self.send_notice(msg.Receiver, CurrentSession.CurrentNick, 'エラー: 返信先のステータスが存在しません。')
					else:
						statuses = []
						try:
							while True:
								reply_to_status = self.deserialize(Status, self.get('/statuses/show/%d.xml' % int(status.InReplyToStatusId)))
								text = self.apply_typablemap(reply_to_status)
								statuses.append((reply_to_status, text))
								if not recursive or not has_reply_to_status_id(reply_to_status):
									break
								status = reply_to_status
						finally:
							# 逆順で流す
							statuses.reverse()
							for status, text in statuses:
								self.send_notice(msg.Receiver, status.User.ScreenName, text)

				def error(e):
					self.send_notice(msg.Receiver, CurrentSession.CurrentNick, 'エラー: 返信先のステータスの取得に失敗しました。')
					self.send_notice(msg.Receiver, CurrentSession.CurrentNick, e.Message)

				self.run_check(msg, command, error)
				return True

			return inner

		# タイムラインを表示する
		def show_timeline(p, msg, status, args):
			def command():
				count = 5 if String.IsNullOrEmpty(args) else int(args)
				statuses = self.deserialize(Statuses, self.get('/statuses/user_timeline.xml?user_id=%d&max_id=%d&count=%d' % (status.User.Id, status.Id, count)))
				statuses = list(statuses.Status)

				statuses.reverse()
				for s in statuses:
					text = self.apply_typablemap(s)
					self.send_notice(msg.Receiver, s.User.ScreenName, text)

			def error(e):
				self.send_notice(msg.Receiver, CurrentSession.CurrentNick, 'エラー: タイムラインの取得に失敗しました。')
				self.send_notice(msg.Receiver, CurrentSession.CurrentNick, e.Message)

			self.run_check(msg, command, error)
			return True

		# register typablemap commands
		self.register('rt', 'Retweet command', retweet)
		self.register('mrt', 'Unofficial retweet command', unofficial_retweet)
		self.register('cv', 'Show conversation command', show_conversation)
		self.register('res', 'Show reply to status command', show_reply_to_status())
		self.register('rres', 'Show recursive reply to status command', show_reply_to_status(True))
		self.register('tl', 'Show timeline command', show_timeline)

# instanciate
typablemap = TypableMap.instance()
