import clr
import re
from Misuzilla.Applications.TwitterIrcGateway import Status, Statuses, User, Users, Utility
from Misuzilla.Applications.TwitterIrcGateway.AddIns import IConfiguration
from Misuzilla.Applications.TwitterIrcGateway.AddIns.Console import ConsoleAddIn, Console, Context
from Misuzilla.Applications.TwitterIrcGateway.AddIns.DLRIntegration import DLRIntegrationAddIn, DLRBasicConfiguration, DLRContextHelper

re_comma = re.compile(r"(\d)(?=(\d{3})+(?!\d))")

def OnTIGGC(sender, e):
	if e.Message.Command.upper() != "TIGGC":
		return
	before = re_comma.sub("\\1,", GC.GetTotalMemory(false))
	GC.Collect()
	after = re_comma.sub("\\1,", GC.GetTotalMemory(false))
	CurrentSession.SendTwitterGatewayServerMessage("Garbage Collect: %s bytes -> %s bytes" % before % after)

def OnBeforeUnload(sender, e):
	Session.PreSendUpdateStatus -= OnTIGGC

CurrentSession.MessageReceived += OnTIGGC
CurrentSession.AddInManager.GetAddIn[DLRIntegrationAddIn]().BeforeUnload += OnBeforeUnload
