---
title: Connect to the corporate VPN with GlobalConnect
category: Network & VPN
tags: vpn, remote work, globalconnect
status: published
visibility: public
owner: alice
---
You need the VPN to reach internal systems (the HR portal, shared drives, PrintHub and the dispatch dashboard) from outside a Halden office. Email and Teams work without it.

## Before you start

- Your laptop must be enrolled in Company Portal. New laptops are enrolled on day one.
- Multi-factor authentication (MFA) must be set up. See *Set up multi-factor authentication*.

## Connect

1. Open **GlobalConnect** from the Start menu (Windows) or the menu bar (macOS). If it's missing, install it from Company Portal.
2. In the portal field, enter `vpn.halden.example`.
3. Sign in with your Halden email and password.
4. Approve the push notification in the Authenticator app.
5. The shield icon turns green when you're connected.

## Good to know

- GlobalConnect replaced the old SecureLink 3 client in March 2026. SecureLink no longer works.
- Sessions disconnect after 12 hours. Reconnect to continue.
- Split tunnelling is on: video calls and public websites don't go through the VPN, which keeps them fast.

If the connection fails with an error number, see *VPN error 809* or contact the Service Desk.
