---
title: Fix Teams audio and video problems
category: Software
tags: teams, audio, video, meetings, troubleshooting
status: published
visibility: public
owner: alice
---
## Others can't hear me, or I can't hear them

1. In the meeting, click **More → Settings → Device settings** and check that the right microphone and speaker are selected. Docking stations often switch them.
2. Check that your headset isn't muted with its own mute button.
3. Leave and rejoin the meeting.

## My camera doesn't work

- Check the privacy shutter on the camera.
- Close other apps that might be using the camera.
- In **Settings → Privacy → Camera**, make sure Teams is allowed.

## Choppy audio or frozen video

- Turn off your incoming video (**More → Turn off incoming video**).
- Move closer to the Wi-Fi access point, or use a cable.
- On the VPN, calls should not be affected because of split tunnelling. If they are, you may still have the old SecureLink client; see *VPN error 809* for removing it.

If problems continue, clear the Teams cache: quit Teams, delete the folder `%appdata%\Microsoft\Teams`, and start Teams again.
