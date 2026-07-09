import React, { useState, useRef, useEffect } from 'react';
import {
  SafeAreaView, View, Text, TextInput, TouchableOpacity, ScrollView,
  ActivityIndicator, StyleSheet, KeyboardAvoidingView, Platform, Linking, Image,
  StatusBar as RNStatusBar,
} from 'react-native';
import { StatusBar } from 'expo-status-bar';
import { useAudioRecorder, RecordingPresets, AudioModule, setAudioModeAsync, createAudioPlayer } from 'expo-audio';
import * as FileSystem from 'expo-file-system/legacy';

const API = 'https://neuro.shadrakbessanh.me';

const T = {
  hi: { greet: 'नमस्ते, आपको क्या लक्षण महसूस हो रहे हैं?', ph: 'यहाँ लिखें...', speak: 'बोलें', write: 'लिखें', mode: 'आप बोलना चाहेंगे या लिखना?', pick: 'भाषा चुनें', listening: 'सुन रहा हूँ...', thinking: 'सोच रहा हूँ...', open: 'आधिकारिक पेज', conf: 'पात्रता विश्वास', voiceTap: 'बोलने के लिए माइक दबाएँ', speaking: 'बोल रहा हूँ...', toText: 'लिखने के लिए', tag: 'आपकी भाषा में सही क्लिनिकल ट्रायल खोजें।', learn: 'और जानें', begin: 'शुरू करें', heroLead: 'हज़ारों मरीज़ इलाज ढूँढते हैं। हज़ारों ट्रायल मरीज़ ढूँढते हैं। हम आवाज़ से, कुछ ही सेकंड में यह पुल बनाते हैं।', howTitle: 'यह कैसे काम करता है', disc: 'मार्गदर्शन उपकरण, निदान नहीं।', code: 'hi-IN' },
  en: { greet: 'Hello, what symptoms are you feeling?', ph: 'Type here...', speak: 'Speak', write: 'Write', mode: 'Would you like to speak or type?', pick: 'Choose your language', listening: 'Listening...', thinking: 'Thinking...', open: 'Official page', conf: 'Eligibility confidence', voiceTap: 'Tap the mic and speak', speaking: 'Speaking...', toText: 'Switch to typing', tag: 'Find the right clinical trial, in your language.', learn: 'Learn more', begin: 'Start', heroLead: 'Thousands of patients search for treatment. Thousands of trials search for patients. We build the bridge — by voice, in seconds.', howTitle: 'How it works', disc: 'Orientation tool, not a diagnosis.', code: 'en-IN' },
  fr: { greet: 'Bonjour, quels symptomes ressentez-vous ?', ph: 'Ecrivez ici...', speak: 'Parler', write: 'Ecrire', mode: 'Voulez-vous parler ou ecrire ?', pick: 'Choisissez votre langue', listening: 'Ecoute...', thinking: 'Reflexion...', open: 'Page officielle', conf: 'Confiance eligibilite', voiceTap: 'Touchez le micro et parlez', speaking: 'Reponse...', toText: 'Passer a l\'ecriture', tag: 'Trouvez le bon essai clinique, dans votre langue.', learn: 'En savoir plus', begin: 'Commencer', heroLead: 'Des milliers de patients cherchent un traitement. Des milliers d\'essais cherchent des patients. Nous construisons le pont, a la voix, en quelques secondes.', howTitle: 'Comment ca marche', disc: 'Outil d\'orientation, pas un diagnostic.', code: 'fr-FR' },
};

const CRIT_IC = { met: '✓', unmet: '✗', unknown: '?', na: '–' };
const confColor = (c) => (c >= 66 ? '#0E7C66' : c >= 40 ? '#C77D2E' : '#E4573B');
const critColor = (st) => (st === 'met' ? '#0E7C66' : st === 'unmet' ? '#E4573B' : '#8A8577');

const STEPS = {
  hi: [['सुनना', 'अपनी भाषा में बोलें; आवाज़ पाठ बन जाती है।'], ['विश्लेषण', 'आपके शब्दों से मुख्य लक्षण निकाले जाते हैं।'], ['मिलान', 'असली भर्ती-वाले ट्रायल खोजे और AI से पुनः क्रमबद्ध किए जाते हैं।'], ['मार्गदर्शन', 'हर परिणाम बताता है कि वह क्यों उपयुक्त है और आगे कैसे बढ़ें।']],
  en: [['Listen', 'Speak in your language; your voice becomes text.'], ['Analyze', 'Key symptoms are pulled from your words.'], ['Match', 'Real recruiting trials are retrieved and re-ranked by AI.'], ['Guide', 'Each result explains why it fits and how to proceed.']],
  fr: [['Ecoute', 'Parlez dans votre langue; la parole devient du texte.'], ['Analyse', 'Les symptomes cles sont extraits de vos mots.'], ['Correspondance', 'De vrais essais qui recrutent sont trouves et reclasses par IA.'], ['Guide', 'Chaque resultat explique pourquoi il convient et comment proceder.']],
};

export default function App() {
  const [step, setStep] = useState('splash');    // splash -> lang -> mode -> chat
  const [lang, setLang] = useState('hi');
  const [messages, setMessages] = useState([]);
  const [history, setHistory] = useState([]);     // english context for the model
  const [input, setInput] = useState('');
  const [busy, setBusy] = useState(false);
  const [recording, setRecording] = useState(false);
  const [mode, setMode] = useState('write');       // 'speak' | 'write' — decides auto voice
  const [voiceGreeted, setVoiceGreeted] = useState(false);
  const audioRecorder = useAudioRecorder(RecordingPresets.HIGH_QUALITY);
  const scroller = useRef(null);
  const t = (k) => (T[lang] && T[lang][k]) || T.en[k];

  useEffect(() => {
    if (step !== 'splash') return;
    const id = setTimeout(() => setStep('lang'), 1600);
    return () => clearTimeout(id);
  }, [step]);

  // A l'arrivee sur l'ecran audio : on pose une premiere question a voix haute, dans la langue
  useEffect(() => {
    if (step !== 'voice' || voiceGreeted) return;
    setVoiceGreeted(true);
    const id = setTimeout(() => speak(t('greet')), 500);
    return () => clearTimeout(id);
  }, [step, voiceGreeted]);

  const LangBar = ({ showBrand = true }) => (
    <View style={s.bar}>
      {showBrand ? <Text style={s.brand}>Neuro-Synthetix</Text> : <View />}
      <View style={s.langPills}>
        {['hi', 'en', 'fr'].map((k) => (
          <TouchableOpacity key={k} onPress={() => setLang(k)} style={[s.pill, lang === k && s.pillOn]}>
            <Text style={[s.pillTxt, lang === k && s.pillTxtOn]}>{k.toUpperCase()}</Text>
          </TouchableOpacity>
        ))}
      </View>
    </View>
  );

  const startChat = (m) => {
    setMode(m);
    setVoiceGreeted(false);
    setMessages([{ role: 'bot', text: t('greet') }]);
    setHistory([{ role: 'assistant', content: T.en.greet }]);
    setStep(m === 'speak' ? 'voice' : 'chat');
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
      if (mode === 'speak') speak(d.reply);   // audio only in voice mode, never when typing
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

  // Push-to-talk : appuyer = enregistre, relacher = envoie pour traitement
  async function pttStart() {
    if (busy) return;
    try {
      const perm = await AudioModule.requestRecordingPermissionsAsync();
      if (!perm.granted) return;
      await setAudioModeAsync({ allowsRecording: true, playsInSilentMode: true });
      await audioRecorder.prepareToRecordAsync();
      audioRecorder.record();
      setRecording(true);
    } catch (e) { setRecording(false); }
  }
  async function pttStop() {
    if (!recording) return;
    try {
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
  if (step === 'splash') {
    return (
      <SafeAreaView style={s.splash}>
        <StatusBar style="dark" />
        <Image source={require('./assets/logo.png')} style={s.splashImg} resizeMode="contain" />
        <ActivityIndicator color="#0E7C66" style={{ marginTop: 20 }} />
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
      <SafeAreaView style={s.app}>
        <StatusBar style="dark" />
        <LangBar />
        <View style={[s.center, { paddingTop: 0 }]}>
          <Text style={s.h1}>{t('mode')}</Text>
          <View style={{ flexDirection: 'row', gap: 14, marginTop: 20 }}>
            <TouchableOpacity style={[s.modeBtn, s.modePrimary]} onPress={() => startChat('speak')}>
              <Text style={s.modeIcon}>🎙️</Text><Text style={s.modeTxt}>{t('speak')}</Text>
            </TouchableOpacity>
            <TouchableOpacity style={s.modeBtn} onPress={() => startChat('write')}>
              <Text style={s.modeIcon}>⌨️</Text><Text style={s.modeTxt}>{t('write')}</Text>
            </TouchableOpacity>
          </View>
        </View>
      </SafeAreaView>
    );
  }

  /* ----- voice mode ----- */
  if (step === 'voice') {
    const hasExchange = messages.some((m) => m.role === 'user');
    const lastBot = hasExchange ? [...messages].reverse().find((m) => m.role === 'bot') : null;
    const status = recording ? t('listening') : busy ? t('thinking') : t('voiceTap');
    return (
      <SafeAreaView style={s.app}>
        <StatusBar style="dark" />
        <LangBar />
        {/* micro centre */}
        <View style={s.vCenter}>
          <Text style={s.vStatus}>{status}</Text>
          <TouchableOpacity
            style={[s.vMic, recording && s.vMicOn]}
            activeOpacity={0.9}
            onPressIn={pttStart}
            onPressOut={pttStop}
            disabled={busy}
          >
            {busy ? <ActivityIndicator color="#fff" size="large" />
              : <Text style={{ fontSize: 52 }}>🎙️</Text>}
          </TouchableOpacity>
          <Text style={s.vHint}>{t('voiceTap')}</Text>
        </View>
        {/* resultats (uniquement apres un vrai echange) */}
        {lastBot ? (
          <ScrollView style={{ maxHeight: 260 }} contentContainerStyle={{ padding: 18, paddingTop: 0 }}>
            <View style={s.vReplyBox}>
              <Text style={s.vReply}>{lastBot.text}</Text>
              <TouchableOpacity style={s.vSpeak} onPress={() => speak(lastBot.text)}>
                <Text style={{ fontSize: 15 }}>🔊</Text>
              </TouchableOpacity>
            </View>
            {(lastBot.trials || []).slice(0, 4).map((x, j) => (
              <View key={j} style={[s.trial, { width: '100%' }]}>
                <Text style={s.trialTitle}>{x.title || x.nct_id}</Text>
                {x.reason ? <Text style={s.trialWhy}>{x.reason}</Text> : null}
                {typeof x.confidence === 'number' ? (
                  <Text style={[s.confVal, { color: confColor(x.confidence), marginTop: 6 }]}>{t('conf')}: {x.confidence}%</Text>
                ) : null}
                <Text style={s.trialMeta}>{x.condition} · {x.nct_id}</Text>
                {x.url ? <Text style={s.link} onPress={() => Linking.openURL(x.url)}>{t('open')} →</Text> : null}
              </View>
            ))}
          </ScrollView>
        ) : null}
        {/* bouton tout en bas */}
        <TouchableOpacity style={s.vBottom} onPress={() => setStep('chat')}>
          <Text style={s.learn}>⌨️  {t('toText')}</Text>
        </TouchableOpacity>
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
      <LangBar />
      <ScrollView ref={scroller} style={s.thread} contentContainerStyle={{ padding: 16 }}
        keyboardShouldPersistTaps="handled" keyboardDismissMode="interactive">
        {messages.map((m, i) => (
          <View key={i} style={[s.row, m.role === 'user' ? s.rowUser : s.rowBot]}>
            <View style={[s.bubble, m.role === 'user' ? s.bubbleUser : s.bubbleBot]}>
              <Text style={m.role === 'user' ? s.tUser : s.tBot}>{m.text}</Text>
            </View>
            {m.role === 'bot' && m.text ? (
              <TouchableOpacity style={s.speakBtn} onPress={() => speak(m.text)}>
                <Text style={s.speakTxt}>🔊</Text>
              </TouchableOpacity>
            ) : null}
            {m.trials && m.trials.slice(0, 4).map((x, j) => (
              <View key={j} style={s.trial}>
                <Text style={s.trialTitle}>{x.title || x.nct_id}</Text>
                {x.reason ? <Text style={s.trialWhy}>{x.reason}</Text> : null}
                {typeof x.confidence === 'number' ? (
                  <View style={{ marginTop: 8 }}>
                    <View style={{ flexDirection: 'row', justifyContent: 'space-between' }}>
                      <Text style={s.confLab}>{t('conf')}</Text>
                      <Text style={[s.confVal, { color: confColor(x.confidence) }]}>{x.confidence}%</Text>
                    </View>
                    <View style={s.confBar}><View style={{ height: 6, borderRadius: 5, width: (x.confidence + '%'), backgroundColor: confColor(x.confidence) }} /></View>
                  </View>
                ) : null}
                {(x.criteria_match || []).map((cr, k) => (
                  <View key={k} style={s.critRow}>
                    <Text style={[s.critIc, { color: critColor(cr.status) }]}>{CRIT_IC[cr.status] || '?'}</Text>
                    <Text style={s.critLab}>{cr.label}</Text>
                  </View>
                ))}
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
  splash: { flex: 1, backgroundColor: '#FFFFFF', alignItems: 'center', justifyContent: 'center' },
  splashImg: { width: 240, height: 240 },
  vCenter: { flex: 1, alignItems: 'center', justifyContent: 'center', padding: 22 },
  vHint: { marginTop: 20, fontSize: 13, color: '#8A8577', textAlign: 'center' },
  vBottom: { paddingVertical: 16, alignItems: 'center', borderTopWidth: 1, borderTopColor: '#E6DFD4' },
  vStatus: { fontSize: 17, fontWeight: '700', color: '#4A5560', marginBottom: 30, textAlign: 'center' },
  vMic: { width: 128, height: 128, borderRadius: 64, backgroundColor: '#0E7C66', alignItems: 'center', justifyContent: 'center', shadowColor: '#0E7C66', shadowOpacity: 0.35, shadowRadius: 20, shadowOffset: { width: 0, height: 10 }, elevation: 8 },
  vMicOn: { backgroundColor: '#E4573B', shadowColor: '#E4573B' },
  vReplyBox: { backgroundColor: '#fff', borderWidth: 1, borderColor: '#E6DFD4', borderRadius: 16, padding: 15, marginTop: 30, width: '100%' },
  vReply: { fontSize: 15.5, color: '#14181C', lineHeight: 22 },
  vSpeak: { alignSelf: 'flex-start', marginTop: 10, paddingVertical: 4, paddingHorizontal: 10, borderRadius: 10, backgroundColor: '#EFEAE0' },
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
  bar: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', paddingHorizontal: 14, paddingVertical: 10, borderBottomWidth: 1, borderBottomColor: '#E6DFD4', backgroundColor: '#FAF7F2' },
  brand: { fontWeight: '700', fontSize: 16, color: '#14181C' }, lang: { fontWeight: '700', color: '#0A5C4C' },
  langPills: { flexDirection: 'row', gap: 6 },
  pill: { paddingHorizontal: 10, paddingVertical: 5, borderRadius: 9, borderWidth: 1.2, borderColor: '#DED6C8', backgroundColor: '#fff' },
  pillOn: { backgroundColor: '#0E7C66', borderColor: '#0E7C66' },
  pillTxt: { fontSize: 12, fontWeight: '700', color: '#6B7680' },
  pillTxtOn: { color: '#fff' },
  heroTitle: { fontSize: 26, fontWeight: '800', color: '#14181C', marginTop: 16, lineHeight: 32 },
  heroLead: { fontSize: 15, color: '#4A5560', marginTop: 12, lineHeight: 22 },
  howTitle: { fontSize: 13, fontWeight: '700', letterSpacing: 1.4, color: '#0A5C4C', marginTop: 36, marginBottom: 6, textTransform: 'uppercase' },
  stepCard: { flexDirection: 'row', gap: 12, alignItems: 'flex-start', backgroundColor: '#fff', borderWidth: 1, borderColor: '#E6DFD4', borderRadius: 14, padding: 14, marginTop: 10 },
  stepNum: { width: 30, height: 30, borderRadius: 9, backgroundColor: '#E8F3EF', alignItems: 'center', justifyContent: 'center' },
  stepNumTxt: { color: '#0A5C4C', fontWeight: '800', fontSize: 15 },
  stepH: { fontWeight: '700', fontSize: 15, color: '#14181C' },
  stepP: { fontSize: 13.5, color: '#6B7680', marginTop: 3, lineHeight: 19 },
  thread: { flex: 1 },
  row: { marginBottom: 16 }, rowUser: { alignItems: 'flex-end' }, rowBot: { alignItems: 'flex-start' },
  speakBtn: { marginTop: 5, paddingVertical: 3, paddingHorizontal: 8, borderRadius: 10, backgroundColor: '#EFEAE0' },
  speakTxt: { fontSize: 14 },
  bubble: { maxWidth: '86%', padding: 12, borderRadius: 16 },
  bubbleBot: { backgroundColor: '#fff', borderWidth: 1, borderColor: '#E6DFD4', borderBottomLeftRadius: 5 },
  bubbleUser: { backgroundColor: '#14181C', borderBottomRightRadius: 5 },
  tBot: { color: '#14181C', fontSize: 15, lineHeight: 21 }, tUser: { color: '#fff', fontSize: 15, lineHeight: 21 },
  trial: { backgroundColor: '#fff', borderWidth: 1, borderColor: '#E6DFD4', borderLeftWidth: 4, borderLeftColor: '#0E7C66', borderRadius: 12, padding: 12, marginTop: 8, width: '96%' },
  trialTitle: { fontWeight: '700', color: '#14181C', fontSize: 14 },
  trialWhy: { color: '#0A5C4C', fontSize: 13, marginTop: 3 },
  confLab: { fontSize: 11, fontWeight: '700', letterSpacing: 0.4, color: '#8A8577', textTransform: 'uppercase' },
  confVal: { fontSize: 12, fontWeight: '800' },
  confBar: { height: 6, borderRadius: 5, backgroundColor: '#EDE6DA', overflow: 'hidden', marginTop: 3 },
  critRow: { flexDirection: 'row', gap: 7, alignItems: 'flex-start', marginTop: 4 },
  critIc: { fontSize: 13, fontWeight: '800', width: 13, textAlign: 'center' },
  critLab: { flex: 1, fontSize: 13, color: '#4A5560', lineHeight: 18 },
  trialMeta: { color: '#6B7680', fontSize: 12, marginTop: 3 },
  link: { color: '#0A5C4C', fontWeight: '700', marginTop: 8, fontSize: 13 },
  composer: { flexDirection: 'row', alignItems: 'flex-end', padding: 12, gap: 8, borderTopWidth: 1, borderTopColor: '#E6DFD4', backgroundColor: '#FAF7F2' },
  mic: { width: 46, height: 46, borderRadius: 14, borderWidth: 1.5, borderColor: '#DED6C8', backgroundColor: '#fff', alignItems: 'center', justifyContent: 'center' },
  micRec: { backgroundColor: '#E4573B', borderColor: '#E4573B' },
  input: { flex: 1, minHeight: 46, maxHeight: 120, borderWidth: 1.5, borderColor: '#DED6C8', borderRadius: 16, paddingHorizontal: 14, paddingTop: 12, backgroundColor: '#fff', color: '#14181C', fontSize: 15 },
  send: { width: 46, height: 46, borderRadius: 14, backgroundColor: '#E4573B', alignItems: 'center', justifyContent: 'center' },
  foot: { textAlign: 'center', color: '#8A8577', fontSize: 11, paddingBottom: 8 },
});
