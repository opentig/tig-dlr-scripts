#!/usr/bin/env python
# -*- coding: utf-8 -*-
from System import DateTime
from System.IO import StringReader
from Misuzilla.Applications.TwitterIrcGateway.AddIns.DLRIntegration import DLRIntegrationAddIn
from Misuzilla.Applications.TwitterIrcGateway import NilClasses, Status, Statuses, User, Users, Utility

''' 
ファイル名とかいじって最後に読み込まれるようにしないとうまく動かないと思います。
RES_PREFIX とか RES_FORMAT あたりを自分の好みに書き換えるといいかもしれません。
'''

# utils {{{
class Utils(object):
    @classmethod
    def urlencode(cls, **params):
        def escape(x):
            return Utility.UrlEncode(str(x))
        return '&'.join(['%s=%s' % (escape(k), escape(v)) for k, v in params.iteritems()])

    @classmethod
    def get(cls, url, **params):
        ''' 指定した URL に GET リクエストを発行します '''
        query = cls.urlencode(**params)
        if query:
            url += '?' + query
        return CurrentSession.TwitterService.GET(url)

    @classmethod
    def post(cls, url, **params):
        ''' 指定した URL に POST リクエストを発行します '''
        query = cls.urlencode(**params)
        return CurrentSession.TwitterService.POST(url, query)

    @classmethod
    def deserialize(cls, type, xml):
        ''' 指定した型で XML のデシリアライズを行ないます '''
        if NilClasses.CanDeserialize(xml):
            raise DeserializeFailedError
        else:
            return type.Serializer.Deserialize(StringReader(xml))

    @classmethod
    def get_status(cls, id):
        ''' ID からステータスを取得します '''
        return cls.deserialize(Status, cls.get('/statuses/show.xml', id=id))
# }}}

class DisplayReplyToStatus(object):

    RES_PREFIX = '\r\n    '
    RES_FORMAT = '>> %(screen_name)s: %(text)s'
    RES_COLOR = None # see: http://www.mirc.co.uk/help/colors.html
    LRU_TIMEOUT = 1 * 60 * 60
    LRU_INTERVAL = LRU_TIMEOUT

    def __init__(self):
        CurrentSession.PreSendMessageTimelineStatus += self.on_pre_send_message_timeline_status
        CurrentSession.AddInManager.GetAddIn(DLRIntegrationAddIn).BeforeUnload += self.on_before_unload
        self.cache = {}
        self.last_lru_time = DateTime.Now

    @classmethod
    def is_expired(cls, new, old, timeout):
        return (new - old).TotalSeconds >= timeout

    @classmethod
    def colored(cls, text, color):
        if color is not None:
            return '%c%d%s%c' % (chr(0x03), color, text, chr(0x03))
        else:
            return text

    def lru(self):
        now = DateTime.Now
        if not self.is_expired(now, self.last_lru_time, self.LRU_INTERVAL):
            return

        for key in self.cache:
            entry = self.cache[key]
            if self.is_expired(now, entry['expire'], self.LRU_TIMEOUT):
                del self.cache[key]

        last_lru_time = now

    def get_reply_to_status(self, status):
        self.lru()

        res_id = status.InReplyToStatusId
        if not res_id:
            return None

        res_id = int(res_id)
        res_status = None
        now = DateTime.Now

        if res_id in self.cache:
            entry = self.cache[res_id]
            if self.is_expired(now, entry['expire'], self.LRU_TIMEOUT):
                del self.cache[res_id]
            else:
                res_status = entry['status']
                entry['expire'] = DateTime.Now

        if res_status is None:
            res_status = Utils.get_status(res_id)
            cached_status = {
                    'screen_name': res_status.User.ScreenName,
                    'text': res_status.Text,
                }
            self.cache[res_id] = {'status': cached_status, 'expire': now}
            return cached_status

    def on_pre_send_message_timeline_status(self, sender, e):
        res_status = self.get_reply_to_status(e.Status)
        if res_status:
            e.Text = '%s%s%s' % (e.Text, self.RES_PREFIX, self.colored(self.RES_FORMAT % res_status, self.RES_COLOR))

    def on_before_unload(self, sender, e):
        CurrentSession.PreSendMessageTimelineStatus -= self.on_pre_send_message_timeline_status


# instance
DisplayReplyToStatus()

