import sys
import clr
import thread

import Misuzilla.Applications.TwitterIrcGateway
import Misuzilla.Applications.TwitterIrcGateway.AddIns

from System import *
from System.Threading import Thread, ThreadStart
from System.Collections.Generic import *
from System.Diagnostics import Trace
from Misuzilla.Applications.TwitterIrcGateway import Status, Statuses, User, Users, Utility
from Misuzilla.Applications.TwitterIrcGateway.AddIns.DLRIntegration import DLRIntegrationAddIn, DLRBasicConfiguration, DLRContextHelper

class NotifyFlowVelocity(Object):
    @classmethod
    def instance(klass):
        if not hasattr(klass, 'instance_'):
            klass.instance_ = NotifyFlowVelocity()
        return klass.instance_

    def __init__(self):
        # 普通の #Console にコンテキストを追加する
        CurrentSession.AddInManager.GetAddIn[DLRIntegrationAddIn]().BeforeUnload += self.onBeforeUnload
        CurrentSession.PostProcessTimelineStatuses += self.onPostProcessTimelineStatuses
        self.running = False
        self.thread = None

        self.total_status_count = 0
        self.status_count = 0
        self.notify_count = 1

    def start(self):
        if not self.running:
            self.thread = Thread(ThreadStart(self.runProc))
            self.thread.Start()

    def runProc(self):
        self.running = True
        while 1:
            Thread.Sleep(60 * 60 * 1000)
            try:
                self.notify()
            except:
                Trace.WriteLine(sys.exc_info().ToString())
        self.running = False

    def notify(self):
        self.total_status_count += self.status_count
        CurrentSession.SendTwitterGatewayServerMessage("Twitterの流速は 現在: %d, 平均: %d です。" % (self.status_count, self.total_status_count / self.notify_count))
        self.status_count = 0
        self.notify_count += 1

    def onPostProcessTimelineStatuses(self, sender, e):
        if not e.IsFirstTime:
            self.status_count += len(e.Statuses.Status)

    def onBeforeUnload(self, sender, e):
        CurrentSession.PostProcessTimelineStatuses -= self.onPostProcessTimelineStatuses
        self.thread.Abort()
        self.thread.Join(5000)

notifyFlowVelocity = NotifyFlowVelocity.instance()
notifyFlowVelocity.start()
