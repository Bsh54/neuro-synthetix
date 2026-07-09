# Public mobile link

Open in **Expo Go** (Android / iOS):

```
exp://qzkabn0-bsh54-8081.exp.direct
```

QR code: `expo-qr.png` (scan it with the Expo Go app).

Hosted on the project VPS (systemd service `neuro-expo`, auto-restart). The link
stays public as long as the server is up. If the tunnel is restarted and the
sub-domain changes, regenerate the QR from the new URL with:

```
https://api.qrserver.com/v1/create-qr-code/?size=420x420&data=<new exp:// url>
```
