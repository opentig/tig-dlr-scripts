import clr
from Misuzilla.Applications.TwitterIrcGateway.AddIns.DLRIntegration import DLRIntegrationAddIn, DLRBasicConfiguration, DLRContextHelper

class DisplayIcon(object):
	def __init__(self):
		CurrentSession.MessageReceived += self.on_message_received
		CurrentSession.PreSendMessageTimelineStatus += self.on_pre_send_message_timeline_status
		CurrentSession.AddInManager.GetAddIn(DLRIntegrationAddIn).BeforeUnload += self.on_before_unload
		self.display = False

	def on_message_received(self, sender, e):
		command = e.Message.Command.upper()
		notice = False

		if command == "ENABLEICON":
			self.display = True
			notice = True
		elif command == "DISABLEICON":
			self.display = False
			notice = True
		elif command == "TOGGLEICON":
			self.display = not self.display
			notice = True

		if notice:
			message = "アイコンの表示を%s化しました。" % ("有効" if self.display else "無効")
			CurrentSession.SendTwitterGatewayServerMessage(message)

	def on_pre_send_message_timeline_status(self, sender, e):
		if self.display:
			e.Text = e.Text + " " + e.Status.User.ProfileImageUrl

	def on_before_unload(self, sender, e):
		CurrentSession.MessageReceived -= self.on_message_received
		CurrentSession.PreSendMessageTimelineStatus -= self.on_pre_send_message_timeline_status

display_icon = DisplayIcon()
