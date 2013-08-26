#!/usr/bin/env python
# -*- encoding: utf-8 -*-
# imports {{{1
import sys
import re
from System import String
from System.Text import Encoding
from System.Net import WebClient, WebException
from System.Collections.Generic import List
from Misuzilla.Applications.TwitterIrcGateway import Status, User, Utility
from Misuzilla.Applications.TwitterIrcGateway.AddIns import TypableMapSupport, ShortenUrlService
from Misuzilla.Applications.TwitterIrcGateway.AddIns.DLRIntegration import DLRIntegrationAddIn
from Newtonsoft.Json import JsonConvert

# exceptions {{{1
class TypableMapError(Exception): pass
class DeserializeFailedError(Exception): pass

# helpers {{{
def urlencode(params):
    def escape(x):
        return Utility.UrlEncode(unicode(x))
    return '&'.join(['%s=%s' % (escape(k), escape(v)) for (k, v) in params.items()])

def request(method, path, endpoint=None, fmt='json', **params):
    if endpoint is None:
        endpoint = path
    query = urlencode(params)
    url = '%s.%s' % (path, fmt)
    if method == 'GET':
        if query:
            url += '?' + query
        return CurrentSession.TwitterService.GETv1_1(url, endpoint)
    else:
        return CurrentSession.TwitterService.POSTv1_1(url, query, endpoint)

def deserialize(type, data):
    return JsonConvert.DeserializeObject[type].Overloads[String](data)

def get_status(id):
    return deserialize(Status, request('GET', '/statuses/show', id=id))

def get_user(id):
    return deserialize(User, request('GET', '/users/show', user_id=id))

# bases {{{1
class TypableMapCommand(object): # {{{2
    def __init__(self, manager, processor, msg, status, args):
        self.manager = manager
        self.processor = processor
        self.msg = msg
        self.status = status
        self.args = args

    def update(self, text, receiver=None, in_reply_to_id=None):
        ''' Twitter のステータスを更新します '''
        if receiver is None:
            receiver = self.msg.Receiver

        if in_reply_to_id is None:
            CurrentSession.UpdateStatusWithReceiver(receiver, text)
        else:
            CurrentSession.UpdateStatusWithReceiver(receiver, text, in_reply_to_id)

    def update_deferred(self, text, receiver=None, in_reply_to_id=None):
        ''' 設定された時間待機したあとに Twitter のステータスを更新します '''
        if receiver is None:
            receiver = self.msg.Receiver

        if in_reply_to_id is None:
            CurrentSession.UpdateStatusWithReceiverDeferred(receiver, text)
        else:
            CurrentSession.UpdateStatusWithReceiverDeferred(receiver, text, in_reply_to_id)

    def notice(self, text, receiver=None, nick=None):
        ''' 指定したチャンネルに NOTICE を送信します '''
        if receiver is None:
            receiver = self.msg.Receiver
        if nick is None:
            nick = CurrentSession.CurrentNick

        CurrentSession.SendChannelMessage(receiver, nick, text, True, False, False, True)

    def apply_typablemap(self, status, text=None):
        ''' TypableMap を適用します '''
        if text is None:
            text = status.Text

        if CurrentSession.Config.EnableTypableMap:
            cno = CurrentSession.Config.TypableMapKeyColorNumber
            id = self.manager.typablemap_commands.TypableMap.Add(status)
            if cno < 0:
                text += ' (%s)' % (id)
            else:
                text += ' %c%d(%s)%c' % (chr(0x03), cno, id, chr(0x03))

        return text

    def shorten_url(self, url, timeout=None):
        ''' URL を短縮します '''
        if timeout is None:
            # デフォルトの1000ミリ秒だと割とタイムアウトするので
            #timeout = self.manager.shorten_url_service.Timeout
            timeout = 3 * 1000
        return self.manager.shorten_url_service.ShortenUrl(url, timeout)

    def process(self):
        raise NotImplementedError

    def error(self, e):
        self.notice(e.Message)

class TypableMapCommandManager(object): # {{{2
    def __init__(self):
        CurrentSession.AddInManager.GetAddIn[DLRIntegrationAddIn]().BeforeUnload += self.on_before_unload
        self.typablemap_commands = CurrentSession.AddInManager.GetAddIn[TypableMapSupport]().TypableMapCommands
        self.shorten_url_service = CurrentSession.AddInManager.GetAddIn[ShortenUrlService]()
        self.commands = []

    def on_before_unload(self, sender, e):
        for command in self.commands:
            self.typablemap_commands.RemoveCommand(command)
        self.commands = []

    def register(self, command, desc, command_type):
        ''' コマンドを登録します '''
        def inner(p, msg, status, args):
            try:
                c = command_type(self, p, msg, status, args)
                CurrentSession.RunCheck(lambda: c.process(), lambda e: c.error(e))
            except:
                (type, value, traceback) = sys.exc_info()
                receiver = msg.Receiver
                nick = CurrentSession.CurrentNick
                CurrentSession.SendChannelMessage(receiver, nick, unicode(type), True, False, False, True)
                CurrentSession.SendChannelMessage(receiver, nick, unicode(value), True, False, False, True)

        self.commands.append(command)
        self.typablemap_commands.AddCommand(command, desc, inner)

# commands {{{1
class ShowUserInfoCommand(TypableMapCommand): # {{{2
    ''' ユーザ情報を表示します '''
    def process(self):
        user = get_user(self.status.User.Id)
        keys = ['Id', 'ScreenName', 'Name', 'Location', 'Url', 'Description', 'Protected']
        for key in keys:
            if hasattr(user, key):
                value = unicode(getattr(user, key))
                if value:
                    self.notice('%s: %s' % (key, value))

    def error(self, e):
        self.notice('エラー: ユーザ情報の取得に失敗しました。')
        self.notice(e.Message)

class ShowConversationCommand(TypableMapCommand): # {{{2
    ''' search.twitter.com の Show Conversation を表示します '''
    def process(self):
        empty = False
        try:
            client = WebClient()
            client.Encoding = Encoding.UTF8
            client.Headers['Accept'] = 'text/html'
            client.Headers['User-Agent'] = 'Mozilla/4.0 (compatible; MSIE 8.0; Windows NT 6.1; Trident/4.0)'

            body = client.DownloadString('http://search.twitter.com/search/thread/%d' % self.status.Id)
            divs = re.findall(r'<div class="msg">(.*?)</div>', body, re.S)
            if divs:
                for div in divs:
                    match = re.search(r'<a[^>]*>(.*?)</a>.*<span[^>]*>(.*?)</span>', div)
                    name = match.group(1)
                    text = re.sub(r'<[^>]*>', '', match.group(2))
                    self.notice(text, nick=name)
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
                self.notice('会話が存在しません。')

    def error(self, e):
        self.notice('エラー: 会話の取得に失敗しました。')
        self.notice(e.Message)

class ShowReplyToStatusCommand(TypableMapCommand): # {{{2
    ''' 返信先を表示します '''
    def __init__(self, manager, processor, msg, status, args):
        TypableMapCommand.__init__(self, manager, processor, msg, status, args)
        self.recursive = False

    @classmethod
    def has_reply_to_status_id(cls, status):
        if status is None:
            return False
        return bool(status.InReplyToStatusId)

    def process(self):
        status = self.status
        if not self.has_reply_to_status_id(status):
            self.notice('返信先のステータスが存在しません。')
        else:
            statuses = []
            try:
                while True:
                    reply_to_status = get_status(int(status.InReplyToStatusId))
                    text = self.apply_typablemap(reply_to_status)
                    statuses.append((reply_to_status, text))
                    if not self.recursive or not self.has_reply_to_status_id(reply_to_status):
                        break
                    status = reply_to_status
            finally:
                # 逆順で流す
                for status, text in reversed(statuses):
                    text = '%s: %s' % (status.CreatedAt.ToString('HH:mm'), text)
                    self.notice(text, nick=status.User.ScreenName)

    def error(self, e):
        self.notice('エラー: 返信先のステータスの取得に失敗しました。')
        self.notice(e.Message)

class ShowRecursiveReplyToStatusCommand(ShowReplyToStatusCommand): # {{{2
    ''' 返信先を再帰的に表示します '''
    def __init__(self, manager, processor, msg, status, args):
        ShowReplyToStatusCommand.__init__(self, manager, processor, msg, status, args)
        self.recursive = True

class ShowUserTimelineCommand(TypableMapCommand): # {{{2
    ''' ユーザータイムラインを表示します '''
    def __init__(self, manager, processor, msg, status, args):
        TypableMapCommand.__init__(self, manager, processor, msg, status, args)
        self.count = 5

    def process(self):
        count = int(self.args) if self.args else self.count
        statuses = deserialize(List[Status], request('GET', '/statuses/user_timeline',
            user_id=self.status.User.Id,
            max_id=self.status.Id,
            count=count))

        for status in reversed(list(statuses)):
            text = self.apply_typablemap(status)
            text = '%s: %s' % (status.CreatedAt.ToString('HH:mm'), text)
            self.notice(text, nick=status.User.ScreenName)

    def error(self, e):
        self.notice('エラー: ユーザータイムラインの取得に失敗しました。')
        self.notice(e.Message)

class RetweetCommand(TypableMapCommand): # {{{2
    ''' 公式 RT を行ないます '''
    def process(self):
        status = deserialize(Status, request('POST', '/statuses/retweet/%s' % self.status.Id, endpoint='/statuses/retweet'))
        retweeted = status.RetweetedStatus
        self.notice('ユーザ %s のステータス "%s" を RT しました。' % (retweeted.User.ScreenName, retweeted.Text))

    def error(self, e):
        self.notice('エラー: RT に失敗しました。')
        self.notice(e.Message)

class UnofficialRetweetCommand(TypableMapCommand): # {{{2
    ''' 非公式 RT を行います '''
    def __init__(self, manager, processor, msg, status, args):
        TypableMapCommand.__init__(self, manager, processor, msg, status, args)
        self.include_user = False

    def process(self):
        text = '%s ' % self.args if self.args else ''
        user = ' @%s' % self.status.User.ScreenName if self.include_user else ''
        url = self.shorten_url('http://twitter.com/%s/status/%s' % (self.status.User.ScreenName, self.status.Id))

        update_text = '%sRT%s: %s' % (text, user, url)
        self.notice(update_text)
        self.update_deferred(update_text)

class PakuriCommand(TypableMapCommand): # {{{2
    ''' パクツイを行います '''
    def process(self):
        update_text = self.status.Text
        self.notice(update_text)
        self.update_deferred(update_text)

class BlockCommand(TypableMapCommand): # {{{2
    def process(self):
        user = deserialize(User, request('POST', '/blocks/create', user_id=self.status.User.Id))
        self.notice('ユーザ %s をブロックしました。' % (user.ScreenName))

    def error(self, e):
        self.notice('エラー: ブロックに失敗しました。')
        self.notice(e.Message)

class ReportSpamCommand(TypableMapCommand): # {{{2
    def process(self):
        user = deserialize(User, request('POST', '/users/report_spam', user_id=self.status.User.Id))
        self.notice('ユーザ %s をスパム報告しました。' % (user.ScreenName))

    def error(self, e):
        self.notice('エラー: スパム報告に失敗しました。')
        self.notice(e.Message)

# registers {{{1
manager = TypableMapCommandManager()
manager.register('ui', 'Show user info command', ShowUserInfoCommand)
manager.register('tl', 'Show user timeline command', ShowUserTimelineCommand)
manager.register('cv', 'Show conversation command', ShowConversationCommand)
manager.register('res', 'Show reply to status command', ShowReplyToStatusCommand)
manager.register('rres', 'Show recursive reply to status command', ShowRecursiveReplyToStatusCommand)
manager.register('rt', 'retweet command', RetweetCommand)
manager.register('mrt', 'Unofficial retweet command', UnofficialRetweetCommand)
manager.register('cp', 'Pakuri command', PakuriCommand)
manager.register('block', 'Block command', BlockCommand)
manager.register('spam', 'Report spam command', ReportSpamCommand)

