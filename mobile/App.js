import React, { useState, useRef, useEffect } from 'react';
import {
  SafeAreaView, View, Text, TextInput, TouchableOpacity, ScrollView,
  ActivityIndicator, StyleSheet, KeyboardAvoidingView, Platform, Linking,
  StatusBar as RNStatusBar,
} from 'react-native';
import { StatusBar } from 'expo-status-bar';
import { useAudioRecorder, RecordingPresets, AudioModule, setAudioModeAsync, createAudioPlayer } from 'expo-audio';
import * as FileSystem from 'expo-file-system/legacy';

const API = 'https://neuro.shadrakbessanh.me';

const T = {
  hi: { greet: 'नमस्ते, आपको क्या लक्षण महसूस हो रहे हैं?', ph: 'यहाँ लिखें...', speak: 'बोलें', write: 'लिखें', mode: 'आप बोलना चाहेंगे या लिखना?', pick: 'भाषा चुनें', listening: 'सुन रहा हूँ...', thinking: 'सोच रहा हूँ...', open: 'आधिकारिक पेज', tag: 'आपकी भाषा में सही क्लिनिकल ट्रायल खोजें।', learn: 'और जानें', begin: 'शुरू करें', code: 'hi-IN' },
  en: { greet: 'Hello, what symptoms are you feeling?', ph: 'Type here...', speak: 'Speak', write: 'Write', mode: 'Would you like to speak or type?', pick: 'Choose your language', listening: 'Listening...', thinking: 'Thinking...', open: 'Official page', tag: 'Find the right clinical trial, in your language.', learn: 'Learn more', begin: 'Start', code: 'en-IN' },
  fr: { greet: 'Bonjour, quels symptomes ressentez-vous ?', ph: 'Ecrivez ici...', speak: 'Parler', write: 'Ecrire', mode: 'Voulez-vous parler ou ecrire ?', pick: 'Choisissez votre langue', listening: 'Ecoute...', thinking: 'Reflexion...', open: 'Page officielle', tag: 'Trouvez le bon essai clinique, dans votre langue.', learn: 'En savoir plus', begin: 'Commencer', code: 'fr-FR' },
};

export default function App() {
  const [step, setStep] = useState('home');      // home -> lang -> mode -> chat
  const [lang, setLang] = useState('hi');
  const [messages, setMessages] = useState([]);
  const [history, setHistory] = useState([]);     // english context for the model
  const [input, setInput] = useState('');
  const [busy, setBusy] = useState(false);
  const [recording, setRecording] = useState(false);
  const audioRecorder = useAudioRecorder(RecordingPresets.HIGH_QUALITY);
  const scroller = useRef(null);
  const t = (k) => (T[lang] && T[lang][k]) || T.en[k];

  const startChat = (mode) => {
    setMessages([{ role: 'bot', text: t('greet') }]);
    setHistory([{ role: 'assistant', content: T.en.greet }]);
    setStep('chat');
    if (mode === 'speak') setTimeout(record, 400);
  };

  const scroll = () => setTimeout(() => scroller.current && scroller.current.scrollToEnd({ animated: true }), 60);

  async function send(text) {
    if (!text || busy) return;
    setBusy(true);
    setMessages((m) => [...m, { role: 'user', text }]);
    setInput('');
    scroll();
    try {
      const r = await fetch(API + '/chat', {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ history: history.slice(-10), message: text, lang }),
      });
      const d = await r.json();
      if (!d || !d.reply) { setMessages((m) => [...m, { role: 'bot', text: 'Sorry, please try again.' }]); setBusy(false); return; }
      setHistory((h) => [...h, { role: 'user', content: d.user_en || text }, { role: 'assistant', content: d.reply_en || d.reply }]);
      setMessages((m) => [...m, { role: 'bot', text: d.reply, trials: d.trials || [] }]);
      scroll();
      speak(d.reply);
    } catch (e) {
      setMessages((m) => [...m, { role: 'bot', text: 'Network error. Please try again.' }]);
    }
    setBusy(false);
  }

  async function speak(text) {
    try {
      const r = await fetch(API + '/tts', {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text, lang }),
      });
      const d = await r.json();
      if (!d || !d.audio) return;
      const path = FileSystem.cacheDirectory + 'reply.wav';
      await FileSystem.writeAsStringAsync(path, d.audio, { encoding: FileSystem.EncodingType.Base64 });
      const player = createAudioPlayer(path);
      player.play();
    } catch (e) { /* silencieux */ }
  }

  async function record() {
    try {
      if (recording) { await stopRecord(); return; }
      const perm = await AudioModule.requestRecordingPermissionsAsync();
      if (!perm.granted) return;
      await setAudioModeAsync({ allowsRecording: true, playsInSilentMode: true });
      await audioRecorder.prepareToRecordAsync();
      audioRecorder.record();
      setRecording(true);
    } catch (e) { setRecording(false); }
  }

  async function stopRecord() {
    try {
      if (!recording) return;
      setRecording(false);
      await audioRecorder.stop();
      const uri = audioRecorder.uri;
      if (!uri) return;
      setBusy(true);
      const form = new FormData();
      form.append('file', { uri, name: 'audio.m4a', type: 'audio/m4a' });
      const r = await fetch(API + '/stt?lang=' + lang, { method: 'POST', body: form });
      const d = await r.json();
      setBusy(false);
      if (d && d.text && d.text.trim()) send(d.text.trim());
    } catch (e) { setBusy(false); }
  }

  /* ----- welcome screens ----- */
  if (step === 'home') {
    return (
      <SafeAreaView style={s.center}>
        <StatusBar style="dark" />
        <View style={s.logo} />
        <Text style={s.h1}>Neuro-Synthetix</Text>
        <Text style={[s.sub, { maxWidth: 300, textAlign: 'center', marginBottom: 30 }]}>{t('tag')}</Text>
        <TouchableOpacity style={s.startBtn} onPress={() => setStep('lang')}>
          <Text style={s.startTxt}>{t('begin')}</Text>
        </TouchableOpacity>
        <TouchableOpacity style={{ marginTop: 18 }} onPress={() => Linking.openURL(API)}>
          <Text style={s.learn}>{t('learn')} →</Text>
        </TouchableOpacity>
      </SafeAreaView>
    );
  }
  if (step === 'lang') {
    return (
      <SafeAreaView style={s.center}>
        <StatusBar style="dark" />
        <View style={s.logo} />
        <Text style={s.h1}>भाषा चुनें</Text>
        <Text style={s.sub}>Choose your language · Choisissez</Text>
        {[['hi', 'हिन्दी', 'Hindi'], ['en', 'English', 'English'], ['fr', 'Francais', 'French']].map(([k, a, b]) => (
          <TouchableOpacity key={k} style={s.langBtn} onPress={() => { setLang(k); setStep('mode'); }}>
            <Text style={s.langA}>{a}</Text><Text style={s.langB}>{b}</Text>
          </TouchableOpacity>
        ))}
      </SafeAreaView>
    );
  }
  if (step === 'mode') {
    return (
      <SafeAreaView style={s.center}>
        <StatusBar style="dark" />
        <Text style={s.h1}>{t('mode')}</Text>
        <View style={{ flexDirection: 'row', gap: 14, marginTop: 20 }}>
          <TouchableOpacity style={[s.modeBtn, s.modePrimary]} onPress={() => startChat('speak')}>
            <Text style={s.modeIcon}>🎙️</Text><Text style={s.modeTxt}>{t('speak')}</Text>
          </TouchableOpacity>
          <TouchableOpacity style={s.modeBtn} onPress={() => startChat('write')}>
            <Text style={s.modeIcon}>⌨️</Text><Text style={s.modeTxt}>{t('write')}</Text>
          </TouchableOpacity>
        </View>
      </SafeAreaView>
    );
  }

  /* ----- chat ----- */
  return (
    <SafeAreaView style={s.app}>
      <StatusBar style="dark" />
      <KeyboardAvoidingView
        style={{ flex: 1 }}
        behavior={Platform.OS === 'ios' ? 'padding' : 'height'}
        keyboardVerticalOffset={0}
      >
      <View style={s.bar}>
        <Text style={s.brand}>Neuro-Synthetix</Text>
        <TouchableOpacity onPress={() => setStep('lang')}><Text style={s.lang}>{lang.toUpperCase()}</Text></TouchableOpacity>
      </View>
      <ScrollView ref={scroller} style={s.thread} contentContainerStyle={{ padding: 16 }}
        keyboardShouldPersistTaps="handled" keyboardDismissMode="interactive">
        {messages.map((m, i) => (
          <View key={i} style={[s.row, m.role === 'user' ? s.rowUser : s.rowBot]}>
            <View style={[s.bubble, m.role === 'user' ? s.bubbleUser : s.bubbleBot]}>
              <Text style={m.role === 'user' ? s.tUser : s.tBot}>{m.text}</Text>
            </View>
            {m.trials && m.trials.slice(0, 4).map((x, j) => (
              <View key={j} style={s.trial}>
                <Text style={s.trialTitle}>{x.title || x.nct_id}</Text>
                {x.reason ? <Text style={s.trialWhy}>{x.reason}</Text> : null}
                <Text style={s.trialMeta}>{x.condition} · {x.nct_id}</Text>
                {(x.hospitals || [])[0] && x.hospitals[0].name ? (
                  <Text style={s.trialMeta}>{x.hospitals[0].name}{x.hospitals[0].country ? ', ' + x.hospitals[0].country : ''}</Text>
                ) : null}
                {x.url ? <Text style={s.link} onPress={() => Linking.openURL(x.url)}>{t('open')} →</Text> : null}
              </View>
            ))}
          </View>
        ))}
        {busy && <ActivityIndicator color="#0E7C66" style={{ marginTop: 8 }} />}
      </ScrollView>
        <View style={s.composer}>
          <TouchableOpacity style={[s.mic, recording && s.micRec]} onPress={record}>
            <Text style={{ fontSize: 20 }}>{recording ? '■' : '🎙️'}</Text>
          </TouchableOpacity>
          <TextInput style={s.input} value={input} onChangeText={setInput}
            placeholder={t('ph')} placeholderTextColor="#8A8577" multiline />
          <TouchableOpacity style={s.send} onPress={() => send(input.trim())}><Text style={{ color: '#fff', fontSize: 18 }}>➤</Text></TouchableOpacity>
        </View>
        <Text style={s.foot}>Orientation tool. Not a diagnosis.</Text>
      </KeyboardAvoidingView>
    </SafeAreaView>
  );
}

const s = StyleSheet.create({
  app: { flex: 1, backgroundColor: '#FAF7F2', paddingTop: Platform.OS === 'android' ? RNStatusBar.currentHeight : 0 },
  center: { flex: 1, backgroundColor: '#FAF7F2', alignItems: 'center', justifyContent: 'center', padding: 26, paddingTop: Platform.OS === 'android' ? RNStatusBar.currentHeight : 0 },
  logo: { width: 54, height: 54, borderRadius: 16, backgroundColor: '#0E7C66', marginBottom: 16 },
  h1: { fontSize: 24, fontWeight: '700', color: '#14181C', textAlign: 'center' },
  sub: { fontSize: 13, color: '#6B7680', marginTop: 6, marginBottom: 22 },
  langBtn: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', width: '100%', maxWidth: 360, borderWidth: 1.6, borderColor: '#DED6C8', borderRadius: 14, padding: 16, marginBottom: 10, backgroundColor: '#fff' },
  langA: { fontSize: 18, fontWeight: '700', color: '#14181C' }, langB: { fontSize: 13, color: '#6B7680' },
  modeBtn: { alignItems: 'center', borderWidth: 1.6, borderColor: '#DED6C8', borderRadius: 18, paddingVertical: 26, paddingHorizontal: 26, backgroundColor: '#fff', width: 140 },
  modePrimary: { borderColor: '#0E7C66', backgroundColor: '#E8F3EF' },
  modeIcon: { fontSize: 38, marginBottom: 10 }, modeTxt: { fontSize: 17, fontWeight: '700', color: '#14181C' },
  startBtn: { backgroundColor: '#0E7C66', borderRadius: 16, paddingVertical: 16, paddingHorizontal: 60, marginTop: 4 },
  startTxt: { color: '#fff', fontSize: 18, fontWeight: '700', letterSpacing: 0.3 },
  learn: { color: '#0A5C4C', fontSize: 15, fontWeight: '700' },
  bar: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', padding: 14, borderBottomWidth: 1, borderBottomColor: '#E6DFD4', backgroundColor: '#FAF7F2' },
  brand: { fontWeight: '700', fontSize: 17, color: '#14181C' }, lang: { fontWeight: '700', color: '#0A5C4C' },
  thread: { flex: 1 },
  row: { marginBottom: 16 }, rowUser: { alignItems: 'flex-end' }, rowBot: { alignItems: 'flex-start' },
  bubble: { maxWidth: '86%', padding: 12, borderRadius: 16 },
  bubbleBot: { backgroundColor: '#fff', borderWidth: 1, borderColor: '#E6DFD4', borderBottomLeftRadius: 5 },
  bubbleUser: { backgroundColor: '#14181C', borderBottomRightRadius: 5 },
  tBot: { color: '#14181C', fontSize: 15, lineHeight: 21 }, tUser: { color: '#fff', fontSize: 15, lineHeight: 21 },
  trial: { backgroundColor: '#fff', borderWidth: 1, borderColor: '#E6DFD4', borderLeftWidth: 4, borderLeftColor: '#0E7C66', borderRadius: 12, padding: 12, marginTop: 8, width: '96%' },
  trialTitle: { fontWeight: '700', color: '#14181C', fontSize: 14 },
  trialWhy: { color: '#0A5C4C', fontSize: 13, marginTop: 3 },
  trialMeta: { color: '#6B7680', fontSize: 12, marginTop: 3 },
  link: { color: '#0A5C4C', fontWeight: '700', marginTop: 8, fontSize: 13 },
  composer: { flexDirection: 'row', alignItems: 'flex-end', padding: 12, gap: 8, borderTopWidth: 1, borderTopColor: '#E6DFD4', backgroundColor: '#FAF7F2' },
  mic: { width: 46, height: 46, borderRadius: 14, borderWidth: 1.5, borderColor: '#DED6C8', backgroundColor: '#fff', alignItems: 'center', justifyContent: 'center' },
  micRec: { backgroundColor: '#E4573B', borderColor: '#E4573B' },
  input: { flex: 1, minHeight: 46, maxHeight: 120, borderWidth: 1.5, borderColor: '#DED6C8', borderRadius: 16, paddingHorizontal: 14, paddingTop: 12, backgroundColor: '#fff', color: '#14181C', fontSize: 15 },
  send: { width: 46, height: 46, borderRadius: 14, backgroundColor: '#E4573B', alignItems: 'center', justifyContent: 'center' },
  foot: { textAlign: 'center', color: '#8A8577', fontSize: 11, paddingBottom: 8 },
});
