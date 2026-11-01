---
title: Ransomware response runbook (security team)
category: Security
tags: ransomware, incident, runbook, security team
status: published
visibility: private
owner: bob
---
Internal runbook for the security team. Don't share outside the team.

## First 15 minutes

1. **Isolate** affected devices from the network using the endpoint console. Don't power them off; memory evidence is lost.
2. **Disable** the affected user accounts and revoke their sessions.
3. **Page** the incident commander and open an incident bridge.

## First hour

- Identify the ransomware family from the ransom note and file extensions.
- Check backups for the affected file shares; confirm the latest clean snapshot.
- Block known indicators (domains, hashes) at the firewall and email gateway.

## Communication

- Legal and the data protection officer must be told within 1 hour if personal data may be affected.
- Staff communication goes out only through the incident commander.

We do not pay ransoms.
