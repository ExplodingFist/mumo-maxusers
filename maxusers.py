#!/usr/bin/env python
# -*- coding: utf-8
#//////////////////////////////////////////////////////////////////////////////
# maxusers.py - Mumo Maximum Channel User Enforcement
#
# Enforces user limits by individual channels, instead of the entire server. 
#///////////////////////////////////////////////////////////////////////////////
## Copyright (C) 2013 Exploding Fist <expfist@custodela.com>
## Referenced code by Stefan Hacker <dd0t@users.sourceforge.net>
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions
# are met:
#
# - Redistributions of source code must retain the above copyright notice,
#   this list of conditions and the following disclaimer.
# - Redistributions in binary form must reproduce the above copyright notice,
#   this list of conditions and the following disclaimer in the documentation
#   and/or other materials provided with the distribution.
# - Neither the name of the Mumble Developers nor the names of its
#   contributors may be used to endorse or promote products derived from this
#   software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# `AS IS'' AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
# A PARTICULAR PURPOSE ARE DISCLAIMED.  IN NO EVENT SHALL THE FOUNDATION OR
# CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL,
# EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO,
# PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR
# PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF
# LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING
# NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
# SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
#-------------------------------------------------------- -----------------------
# Configuration management
#///////////////////////////////////////////////////////////////////////////////
#
# Module created by: Exploding Fist <expfist@custodela.com>
#
#///////////////////////////////////////////////////////////////////////////////
# Imports
from mumo_module import (commaSeperatedIntegers, commaSeperatedStrings,
                         MumoModule)
import re
#
#///////////////////////////////////////////////////////////////////////////////
# Module configuration

class maxusers(MumoModule):
    default_config = {'maxusers':(
                                ('exceptions', commaSeperatedStrings, []),
                                ('servers', commaSeperatedIntegers, []),
                                ('limit', int, 0),
                                ('ret', int, 0),
                                ),
                      lambda x: re.match('channel_\d+', x):(
                                ('limit', int, 0),
                                )
                    }

#
#///////////////////////////////////////////////////////////////////////////////
# Module Initialization

    def __init__(self, name, manager, configuration = None):
        MumoModule.__init__(self, name, manager, configuration)
        self.murmur = manager.getMurmurModule()
 
        
    def connected(self):
        manager = self.manager()
        log = self.log()
        log.debug("Register for Server callbacks")
        
        servers = self.cfg().maxusers.servers
        if not servers:
            servers = manager.SERVERS_ALL
        manager.subscribeServerCallbacks(self, servers)
        
    def disconnected(self): pass
    
#
#///////////////////////////////////////////////////////////////////////////////
# Call back functions
    
    def userStateChanged(self, server, state, context = None):
        log = self.log()
        sid = server.id()
        #log.debug("User %s state changed on server %i - Channel now: %i", state.name, sid, state.channel)
        # Check if we need to enforce a user limit on this channel
        monitored = 0
        # Channel config
        try:
            curchan = state.channel
            climit = getattr(self.cfg(), 'channel_%d' % curchan)
            monitored = 1
        # Global config
        except:
            if (self.cfg().maxusers.limit > 0):
                climit = self.cfg().maxusers
                curchan = state.channel
                monitored = 1 
        if (monitored == 1):
            log.debug("User %s entered monitored channel %i which has a limit set to %i", state.name, curchan, climit.limit)  
                
            # Get information on all connected users
            userlist = server.getUsers()
            chanCount = 0
            for user in userlist:
 #               log.debug("Debug chan: %s", userlist[user])
                # Count number of users in monitored channel
                if (userlist[user].channel == curchan):
                    chanCount = chanCount + 1
            # Check if now over max
            if (chanCount > climit.limit):
                # Channel is now over limit
                log.info("Channel %i is now over max with %i users connected when there is a max of %i", curchan, chanCount, climit.limit)
                # Where do I move the user back to?
                try:
                    moveto = getattr(maxusers, "%s" % state.name)
                except:
                    # Previous channel isn't stored. Moving to defined return channel.
                    moveto = self.cfg().maxusers.ret
                    
                # Is user an exception to the rule?
                exceptions = self.cfg().maxusers.exceptions
                override = 0
                if exceptions:
                    # Get users ID and list of groups on channel
                    getID = [state.name]
                    userID = server.getUserIds(getID)
                    groupList = server.getACL(state.channel) # Group must exist on channel for exception to work. This is a feature, not a bug. 
                    #log.debug("Debug group: %s", groupList[1])
                    for group in groupList[1]:
                        for exception in exceptions:
                            if (group.name == exception): # Is there an exempted group in the ACL?
                                for members in group.members: # If so, is this user a member?
                                    if (members == userID[state.name]):
                                        override = 1 # Exception found
                                        log.debug("Exception found for user %s joining channel %s since the user is in group %s and %s is exempt from enforcement.",state.name,state.channel,group.name, exception)
                                        server.sendMessage(state.session, 'The channel you attempted to join is limited to a maximum of %i users, and is currently full. However, you have not been moved because you are in an exempt user group.' % climit.limit)
                                        return(1)
                    
                if (override == 0):
                    log.info("Moving user %s to previous channel %s", state.name, moveto) 
                    state.channel = moveto
                    # Move the user back
                    try:
                        server.setState(state)
                        server.sendMessage(state.session, 'The channel you attempted to join is limited to a maximum of %i users, and is currently full.' % climit.limit)
                    except self.murmur.InvalidChannelException:
                        log.error("Moving user '%s' failed, target channel %d does not exist on server %d", state.name, self.cfg().channel, sid)
            else: 
                log.debug("Channel %i is not over max with %i users connected when there is a max of %i", curchan, chanCount, climit.limit)
        else:
            log.debug("User %s entered unmonitored channel %i", state.name, state.channel) # Remove
        
        # Putting users new current channel into memory for later reference
        setattr(maxusers, "%s" % state.name, state.channel)
        testing = getattr(maxusers, "%s" % state.name)
        log.debug("Current channel stored as %s for %s", testing, state.name )
    
    def userConnected(self, server, state, context = None):pass  
    def userDisconnected(self, server, state, context = None): pass
    def userTextMessage(self, server, user, message, current=None): pass
    def channelCreated(self, server, state, context = None): pass
    def channelRemoved(self, server, state, context = None): pass
    def channelStateChanged(self, server, state, context = None): pass
#
#///////////////////////////////////////////////////////////////////////////////
