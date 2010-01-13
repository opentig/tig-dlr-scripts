from System.Diagnostics import Debug, Trace, TraceListener
from System.Reflection import BindingFlags, PropertyInfo
from Misuzilla.Net.Irc import NoticeMessage, PrivMsgMessage
from Misuzilla.Applications.TwitterIrcGateway import TraceLogger
from Misuzilla.Applications.TwitterIrcGateway.AddIns.DLRIntegration import DLRIntegrationAddIn

def get_trace_source(logger):
	type = logger.GetType()
	flags = BindingFlags.Instance | BindingFlags.NonPublic
	property = type.GetProperty('TraceSource', flags)
	return property.GetValue(logger, None)

def enum_trace_sources():
	yield Trace
	#yield Debug
	yield get_trace_source(TraceLogger.Server)
	yield get_trace_source(TraceLogger.Twitter)
	yield get_trace_source(TraceLogger.Filter)
	yield get_trace_source(CurrentSession.Logger)

def send_message(msg, content):
	msg.Sender = 'trace!trace@internal'
	msg.Receiver = '#Trace'
	msg.Content = content
	CurrentSession.Send(msg)

class IrcTraceListener(TraceListener):
	@classmethod
	def instance(klass):
		if not hasattr(klass, 'instance_'):
			klass.instance_ = IrcTraceListener()
		return klass.instance_

	def __init__(self):
		CurrentSession.AddInManager.GetAddIn[DLRIntegrationAddIn]().BeforeUnload += self.on_before_unload
		self.sources = []
		for source in enum_trace_sources():
			self.sources.append(source)
			source.Listeners.Add(self)

	def on_before_unload(self, sender, e):
		for source in self.sources:
			source.Listeners.Remove(self)
		self.sources = []
	
	def Write(self, message):
		self.WriteLine(message)
		pass

	def WriteLine(self, message):
		indent = ' ' * (self.IndentLevel * self.IndentSize)
		for line in message.split('\n'):
			send_message(NoticeMessage(), indent + line)

IrcTraceListener.instance()
