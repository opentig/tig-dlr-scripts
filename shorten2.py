import clr
import re
from System.Net import WebClient
from Misuzilla.Applications.TwitterIrcGateway import Status, Statuses, User, Users, Utility
from Misuzilla.Applications.TwitterIrcGateway.AddIns.DLRIntegration import DLRIntegrationAddIn, DLRBasicConfiguration, DLRContextHelper

re_shorten = re.compile(r"<span.*id=\"short_url\">(.+)</span>")
re_url = re.compile(r"s?https?://[-_.!~*'()a-zA-Z0-9;/?:@&=+$,%#]+")

def OnPreSendUpdateStatus(sender, e):
	try:
		if e.Text.Length < 140:
			return
		for long_url in re_url.findall(e.Text):
			short_url = ShortenUrl(long_url)
			e.Text = e.Text.replace(long_url, short_url)
	except:
		pass

def ShortenUrl(long_url):
	request_url = "http://bit.ly/?url=%s" % (Utility.UrlEncode(long_url))
	client = WebClient()
	response = client.DownloadString(request_url)
	return re_shorten.search(response).group(1)

def OnBeforeUnload(sender, e):
	CurrentSession.PreSendUpdateStatus -= OnPreSendUpdateStatus

CurrentSession.PreSendUpdateStatus += OnPreSendUpdateStatus
CurrentSession.AddInManager.GetAddIn[DLRIntegrationAddIn]().BeforeUnload += OnBeforeUnload
