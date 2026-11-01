---
title: VPN error 809 - the network connection could not be established
category: Network & VPN
tags: vpn, error, globalconnect, troubleshooting
status: published
visibility: public
owner: alice
---
**Error 809** means your computer couldn't reach the VPN gateway at all. It is almost always caused by the network you're on, not by your account.

## Most common causes

| Cause | How to tell | Fix |
|---|---|---|
| Hotel or café Wi-Fi blocks VPN traffic | Works at home, fails on public Wi-Fi | Use your phone's hotspot |
| Home router blocks UDP ports 500 and 4500 | Fails at home on every device | Enable "IPsec passthrough" in the router settings |
| Captive portal not accepted yet | Websites open a login page | Open any website, accept the terms, then reconnect |
| Old SecureLink client still installed | Two VPN icons in the tray | Uninstall SecureLink 3, restart, reconnect with GlobalConnect |

## Still failing?

1. Restart the laptop.
2. In GlobalConnect, click **Settings → Collect logs**.
3. Open a ticket with the Service Desk and attach the log file. Include the network you were on and the time of the error.

Related: *Connect to the corporate VPN with GlobalConnect*.
