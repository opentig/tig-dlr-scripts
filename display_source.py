import sys
import clr
import re

#from System.Windows.Forms import *
from Misuzilla.Applications.TwitterIrcGateway.AddIns.DLRIntegration import DLRIntegrationAddIn, DLRBasicConfiguration, DLRContextHelper

re_source = re.compile(r"<.*?>")

def OnPreSendMessageTimelineStatus(sender, e):
    e.Text = e.Text + " (from "+ re_source.sub("", e.Status.Source) +")"

def OnBeforeUnload(sender, e):
    CurrentSession.PreSendMessageTimelineStatus -= OnPreSendMessageTimelineStatus

CurrentSession.PreSendMessageTimelineStatus += OnPreSendMessageTimelineStatus
CurrentSession.AddInManager.GetAddIn(DLRIntegrationAddIn).BeforeUnload += OnBeforeUnload

