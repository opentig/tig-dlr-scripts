#!/usr/bin/env python
# -*- coding: utf-8 -*-
from System import DateTime
from System.IO import StringReader
from Misuzilla.Applications.TwitterIrcGateway.AddIns.DLRIntegration import DLRIntegrationAddIn
from Misuzilla.Applications.TwitterIrcGateway import NilClasses, Status, Statuses, User, Users, Utility

# settings {{{
RES_PREFIX = ' '
RES_FORMAT = '>> %(screen_name)s: %(text)s'
RES_COLOR = None # see: http://www.mirc.co.uk/help/colors.html
LRU_TIMEOUT = 10 * 60
LRU_INTERVAL = LRU_TIMEOUT
# }}}

class Cache(object): # {{{
    DEFAULT_LRU_INTERVAL = 10 * 60

    def __init__(self, lru_interval=DEFAULT_LRU_INTERVAL):
        self._cache = {}
        self._lru_interval = lru_interval
        self._lru_time = DateTime.Now.AddSeconds(self._lru_interval)

    @classmethod
    def is_expired(cls, dt, now=None):
        if now is None:
            now = DateTime.Now
        if dt:
            return DateTime.Now >= dt
        else:
            return False

    @classmethod
    def _expire(cls, timeout=None, now=None):
        if now is None:
            now = DateTime.Now
        if timeout is None:
            return None
        else:
            return now.AddSeconds(timeout)

    def _lru(self):
        now = DateTime.Now
        if self.is_expired(self._lru_time, now):
            for (k, v) in self._cache.items():
                if self.is_expired(v['expire'], now):
                    self._del(k)
            self._lru_time = self._expire(self._lru_interval, now=now)

    def _del(self, key):
        return self._cache.pop(key, None)

    def set(self, key, value, timeout=None):
        now = DateTime.Now
        self._cache[key] = {
                'value': value,
                'timeout': timeout,
                'expire': self._expire(timeout),
            }

    def get(self, key):
        entry = self._cache.get(key, None)
        if entry is None:
            return None
        elif self.is_expired(entry['expire']):
            self._del(key)
            return None
        else:
            entry['expire'] = self._expire(entry['timeout'])
            return entry['value']

# }}}

class StatusCache(Cache): # {{{

    @classmethod
    def _urlencode(cls, params):
        def escape(x):
            return Utility.UrlEncode(unicode(x))
        return '&'.join(['%s=%s' % (escape(k), escape(v)) for (k, v) in params.items()])

    @classmethod
    def _request(cls, method, url, **params):
        query = cls._urlencode(params)
        if method == 'GET':
            if query:
                url += '?' + query
            return CurrentSession.TwitterService.GET(url)
        else:
            return CurrentSession.TwitterService.POST(url, query)

    @classmethod
    def _deserialize(cls, type, xml):
        if NilClasses.CanDeserialize(xml):
            raise DeserializeFailedError
        else:
            return type.Serializer.Deserialize(StringReader(xml))

    @classmethod
    def _get_status(cls, id):
        return cls._deserialize(Status, cls._request('GET', '/statuses/show.xml', id=id))

    def set(self, status, timeout=None):
        Cache.set(self, status.Id, status, timeout=timeout)

    def get(self, id, timeout=None):
        self._lru()
        if id is None:
            return None

        status = Cache.get(self, id)
        status = None
        if status is None:
            status = self._get_status(id)
            self.set(status, timeout=timeout)
        return status
# }}}

class DisplayReplyToStatus(object): # {{{
    def __init__(self, cache, timeout, prefix, fmt, color):
        CurrentSession.PreSendMessageTimelineStatus += self.on_pre_send_message_timeline_status
        CurrentSession.AddInManager.GetAddIn(DLRIntegrationAddIn).BeforeUnload += self.on_before_unload
        self.cache = cache
        self.timeout = timeout
        self.prefix = prefix
        self.fmt = fmt
        self.color = color

    @classmethod
    def colored(cls, text, color):
        if color is not None:
            return '%c%d%s%c' % (chr(0x03), color, text, chr(0x03))
        else:
            return '%c%s' % (chr(0x03), text)

    @classmethod
    def get_res_id(cls, status):
        res_id = status.InReplyToStatusId
        if not res_id:
            return None
        return int(res_id)

    @classmethod
    def status_to_dict(cls, status):
        return {
            'id': status.Id,
            'created_at': status.CreatedAt,
            'text': status.Text,
            'user_id': status.User.Id,
            'name': status.User.Name,
            'screen_name': status.User.ScreenName,
        }

    def on_pre_send_message_timeline_status(self, sender, e):
        try:
            status = e.Status
            self.cache.set(status, self.timeout)

            res_id = self.get_res_id(status)
            res_status = self.cache.get(res_id, self.timeout)
            if res_status:
                colored_text = self.colored(self.fmt % self.status_to_dict(res_status), self.color)
                e.Text = '%s%s%s' % (e.Text, self.prefix, colored_text)
        except Exception, e:
            e.Text += ' (%s)' % unicode(e)

    def on_before_unload(self, sender, e):
        CurrentSession.PreSendMessageTimelineStatus -= self.on_pre_send_message_timeline_status
# }}}

# instantiate {{{
cache = StatusCache(lru_interval=LRU_INTERVAL)
instance = DisplayReplyToStatus(cache, LRU_TIMEOUT, RES_PREFIX, RES_FORMAT, RES_COLOR)
# }}}

