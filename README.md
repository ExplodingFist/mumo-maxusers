mumo-maxusers
=============

This is a mumo module to allow an administrator the capability of enforcing granular user limits by channel in mumble.

Features:
- Can set a limit to every channel (global config)
- Can specify limits to unlimited individual channels, overriding the global configuration
- Automatically move users back to their previous channel when attempting to join a full channel, while letting them know why they were moved.
- Allow for groups to be exempted from enforcement on channels based on the group/acl applied to the channel

This module should be considered beta for the moment, but is currently being actively used/tested. 
