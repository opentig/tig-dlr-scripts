import re
from Misuzilla.Applications.TwitterIrcGateway.AddIns.DLRIntegration import DLRIntegrationAddIn

re_source = re.compile(r"<.*?>")

def OnPreSendMessageTimelineStatus(sender, e):
    e.Text = e.Text + " (via "+ re_source.sub("", e.Status.Source) +")"

def OnBeforeUnload(sender, e):
    CurrentSession.PreSendMessageTimelineStatus -= OnPreSendMessageTimelineStatus

CurrentSession.PreSendMessageTimelineStatus += OnPreSendMessageTimelineStatus
CurrentSession.AddInManager.GetAddIn(DLRIntegrationAddIn).BeforeUnload += OnBeforeUnload
