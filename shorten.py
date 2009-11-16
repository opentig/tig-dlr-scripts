import clr
import re
from System.Net import WebClient
from Misuzilla.Applications.TwitterIrcGateway import Status, Statuses, User, Users, Utility
from Misuzilla.Applications.TwitterIrcGateway.AddIns.DLRIntegration import DLRIntegrationAddIn, DLRBasicConfiguration, DLRContextHelper

username = "your bit.ly username"
apikey = "your bit.ly apikey"

re_shorten = re.compile(r"<shortUrl>(.+)</shortUrl>")
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
	request_url = "http://api.bit.ly/shorten?version=2.0.1&format=xml&longUrl=%s&login=%s&apiKey=%s" % (Utility.UrlEncode(long_url), username, apikey)
	client = WebClient()
	result = client.DownloadString(request_url)
	return re_shorten.search(result).group(1)

def OnBeforeUnload(sender, e):
	CurrentSession.PreSendUpdateStatus -= OnPreSendUpdateStatus

CurrentSession.PreSendUpdateStatus += OnPreSendUpdateStatus
CurrentSession.AddInManager.GetAddIn[DLRIntegrationAddIn]().BeforeUnload += OnBeforeUnload
