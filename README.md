# nordvpn-killswitch
Kill switch for the Linux NordVPN app

The Kill Switch feature on the NordVPN Linux app disables system-wide internet
access. This makes it unusable when remote access is needed, such as on a
headless Raspberry Pi.

This script monitors the VPN status and kills specific processes when the VPN
disconnects. It will also attempt to reconnect and restart the processes when
the VPN is back online.
