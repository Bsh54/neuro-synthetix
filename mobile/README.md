# Neuro-Synthetix — Mobile (Expo)

A React Native (Expo) app for the same assistant as the web: chat, real Sarvam
voice (speak and listen), and real clinical-trial results. It talks to the same
backend API (`https://neuro.shadrakbessanh.me`), so nothing else is needed.

## Features
- Welcome flow: choose language (Hindi / English / French) then speak or type.
- Chat with the AI (progressive questions + RAG search).
- Voice: record your symptoms (sent to Sarvam speech-to-text), and the reply is
  spoken back (Sarvam text-to-speech).
- Real trials with a reason, condition, site, and a link to the official page.

## Try it now (no build needed)

Install **Expo Go** on your phone and scan this QR code, or open the link inside Expo Go:

<img src="expo-qr.png" width="220" alt="Scan with Expo Go" />

```
exp://ncarnci-bsh54-8081.exp.direct
```

The app is hosted on the project VPS, so the link stays public as long as the server runs.

## Run it

```bash
cd mobile
npm install
npx expo start
```

Then:
- Scan the QR code with the **Expo Go** app on your Android/iPhone, or
- press `a` for an Android emulator / `i` for an iOS simulator.

The app needs microphone permission for voice.

## Notes
- The backend is already live, so the app works out of the box.
- Voice recording on device is best-effort per audio format; text always works.
- Built for HackHazards '26 (Expo track).
