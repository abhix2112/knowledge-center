---
title: Outlook keeps asking for my password
category: Email & Calendar
tags: outlook, email, password, troubleshooting
status: published
visibility: public
owner: alice
---
Repeated password prompts in Outlook usually mean it has cached old sign-in details.

## Fix

1. Close Outlook completely, including from the system tray.
2. Open **Credential Manager** (Windows) or **Keychain Access** (macOS).
3. Remove every entry that contains `outlook`, `office` or `halden`.
4. Restart the laptop and open Outlook. Sign in once and approve the MFA request.

## If it keeps happening

- Make sure your laptop's date and time are set automatically. A wrong clock breaks sign-in tokens.
- Check that Outlook is up to date in Company Portal.
- If you recently reset your password, lock and unlock your laptop while connected to the office network or VPN.

Outlook on the web (`mail.halden.example`) keeps working while you fix the desktop app.
