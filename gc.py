import re
from Misuzilla.Applications.TwitterIrcGateway.AddIns.DLRIntegration import DLRIntegrationAddIn

re_comma = re.compile(r"(\d)(?=(\d{3})+(?!\d))")

def OnTIGGC(sender, e):
	if e.Message.Command.upper() != "TIGGC":
		return
	before = re_comma.sub("\\1,", GC.GetTotalMemory(false))
	GC.Collect()
	after = re_comma.sub("\\1,", GC.GetTotalMemory(false))
	CurrentSession.SendTwitterGatewayServerMessage("Garbage Collect: %s bytes -> %s bytes" % before % after)

def OnBeforeUnload(sender, e):
	Session.MessageReceived -= OnTIGGC

CurrentSession.MessageReceived += OnTIGGC
CurrentSession.AddInManager.GetAddIn[DLRIntegrationAddIn]().BeforeUnload += OnBeforeUnload
