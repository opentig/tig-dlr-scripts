# http://twitterircgateway.g.hatena.ne.jp/retlet/20100514/1273811857
import re
from Misuzilla.Applications.TwitterIrcGateway.AddIns.DLRIntegration import DLRIntegrationAddIn

rt_mark_original = unichr(0x267B)
rt_mark_rewrite = unichr(0x267A)
rt_mark_color = CurrentSession.Config.TypableMapKeyColorNumber

def color(str, num):
	escape = chr(0x03)
	return '%c%d%s%c' % (escape, num, str, escape)

def OnPreSendMessageTimelineStatus(sender, e):
	if e.Status.RetweetedStatus != None:
		pattern = r'%s(\sRT\s@[^\s]*)' % rt_mark_original
		replace = color(r'%s\1' % rt_mark_rewrite, rt_mark_color)
		e.Text = re.sub(pattern, replace, e.Text)

def OnBeforeUnload(sender, e):
	CurrentSession.PreSendMessageTimelineStatus -= OnPreSendMessageTimelineStatus

CurrentSession.PreSendMessageTimelineStatus += OnPreSendMessageTimelineStatus
CurrentSession.AddInManager.GetAddIn(DLRIntegrationAddIn).BeforeUnload += OnBeforeUnload
