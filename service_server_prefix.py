#!/usr/bin/python
# -*- encoding: utf-8 -*-
from System import Uri
from System.Net import CredentialCache, NetworkCredential
from System.Reflection import FieldInfo, BindingFlags

prefix = "http://msrprx.appspot.com"
path = "/api"

def _get(instance, name):
	type = instance.GetType()
	field = type.GetField(name, BindingFlags.Instance | BindingFlags.NonPublic)
	return field.GetValue(instance)

def _set(instance, name, value):
	type = instance.GetType()
	field = type.GetField(name, BindingFlags.Instance | BindingFlags.NonPublic)
	field.SetValue(instance, value)

username = CurrentSession.Connections[0].UserInfo.UserName
password = CurrentSession.Connections[0].UserInfo.Password

credential = _get(CurrentSession.TwitterService, "_credential")
credential.Remove(Uri(prefix), "Basic")
credential.Add(Uri(prefix), "Basic", NetworkCredential(username, password))
_set(CurrentSession.TwitterService, "_credential", credential)

CurrentSession.TwitterService.ServiceServerPrefix = prefix + path
