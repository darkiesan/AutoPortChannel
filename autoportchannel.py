#!/usr/bin/env python

import sys, syslog, os
from jsonrpclib import Server

#
# Support functions
#

def interfaceProvisioned( switchName, interfaceName ):
	mySwitch = Server( "unix:/var/run/command-api.sock" )
	result = mySwitch.runCmds(1, [	"enable",
									"show interfaces " + interfaceName] )
	if result[1]["interfaces"][interfaceName]["description"] == "":
		exists = 0
	else:
		exists = 1
	return exists

def macExists( serverMac, Devices ):
	exists = 0
	for device in Devices:
		if device["mac1"] == serverMac:
			exists = 1
		if device["mac2"] == serverMac:
			exists = 1
		if device["mac3"] == serverMac:
			exists = 1
		if device["mac4"] == serverMac:
			exists = 1
	return exists

def getMacData( serverMac, Devices ):
	portChannel = "N/A"
	for device in Devices:
		if device["mac1"] == serverMac:
			portChannel = device["portChannel"]
		if device["mac2"] == serverMac:
			portChannel = device["portChannel"]
		if device["mac3"] == serverMac:
			portChannel = device["portChannel"]
		if device["mac4"] == serverMac:
			portChannel = device["portChannel"]
	return portChannel

def getServerName( serverMac, Devices ):
	name = "N/A"
	for device in Devices:
		if device["mac1"] == serverMac:
			name = device["name"]
		if device["mac2"] == serverMac:
			name = device["name"]
		if device["mac3"] == serverMac:
			name = device["name"]
		if device["mac4"] == serverMac:
			name = device["name"]
	return name

#
# Constants. Edit to suite deployment environment.
#

Devices = [
			{
				"name": "DGX01",
				"portChannel": "1",
				"mac1": "52:54:00:df:fc:03",
				"mac2": "52:54:00:df:fc:04",
				"mac3": "52:54:00:df:fc:05",
				"mac4": "52:54:00:df:fc:06"
			},
			
			{
				"name": "DGX02",
				"portChannel": "2",
				"mac1": "52:54:00:df:fc:07",
				"mac2": "52:54:00:df:fc:08",
				"mac3": "52:54:00:df:fc:09",
				"mac4": "52:54:00:df:fc:10"

			}

			]


#
# Collect cmdline arguments.
#

syslog.openlog('autoportchannel.py', 0, syslog.LOG_DEBUG)
syslog_string = 'autoportchannel.py: Collected cmd line arguments %s %s' % ( os.environ['INTF'] , os.environ['OPERSTATE'] )
syslog.syslog(syslog_string)

interfaceName = os.environ['INTF']
interfaceStatus = os.environ['OPERSTATE']

#
# Only start provisioning cycle and checks if the interface
# operstatus is linkup.
#

if interfaceStatus == "linkup":

#
# Open a socket to self (switch) and collect MAC address
# on interface that went up. Repeat asking for MAC address
# until one appear.
#

	switch = Server( "unix:/var/run/command-api.sock" )
	result = switch.runCmds( 1, [ "show mac address-table interface " + interfaceName ] )

	while result[0]["unicastTable"]["tableEntries"] == []:
		result = switch.runCmds( 1, [ "show mac address-table interface " + interfaceName ] )

	serverMac = result[0]["unicastTable"]["tableEntries"][0]["macAddress"]

	result = switch.runCmds( 1, [ "show hostname" ] )
	switchName = result[0]["fqdn"]
	syslog.openlog('autoportchannel.py', 0, syslog.LOG_DEBUG)
	syslog_string = 'autoportchannel.py: Collected switch FQDN and MAC address of interface going online %s %s' % ( switchName , serverMac )
	syslog.syslog(syslog_string)
#
# If interface is already provisioned, exit script with code 0.
#

	if interfaceProvisioned( switchName, interfaceName ):
		syslog.openlog('autoportchannel.py', 0, syslog.LOG_DEBUG)
		syslog_string = 'autoportchannel.py: Interface was already provisioned:  %s %s' % ( switchName , interfaceName )
		syslog.syslog(syslog_string)
		sys.exit(0)
	
#
# Fetch provisioning data for MAC address. If the address doesnt exist,
# exit script with code 0.
#
 	
	if macExists( serverMac, Devices ):
	 	portChannel = getMacData( serverMac, Devices )
	 	serverName = getServerName( serverMac, Devices )
	else:
		syslog.openlog('autoportchannel.py', 0, syslog.LOG_DEBUG)
		syslog_string = 'autoportchannel.py: MAC address doesnt exist in DB:  %s %s' % ( switchName , serverMac )
		syslog.syslog(syslog_string)
		sys.exit(0)	

#
# MAC address existed in DB, now create configuration
# and apply to switch.
#
	
	result = switch.runCmds(1, ["enable",
								"configure",
								"interface " + interfaceName, 
								"description Member_of_port-Channel" + portChannel,
								"channel-group " + portChannel + " mode active",
								"interface port-Channel" + portChannel,
								"description Connected_to_server_" + serverName,
								"mlag " + portChannel,
								"write memory" ])

else:
	syslog.openlog('autoportchannel.py', 0, syslog.LOG_DEBUG)
	syslog_string = 'autoportchannel.py: Interface event was not linkup, %s' % ( sys.argv[2] )
	syslog.syslog(syslog_string)
	sys.exit(0)