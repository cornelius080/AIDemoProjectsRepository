/**
 * app.js — Gemini Live Frontend
 *
 * Protocol (browser <-> Python WebSocket bridge):
 *  SEND   text  → JSON  { type: "text",  content: "…" }
 *  SEND   audio → binary PCM-16 frames (via AudioWorklet)
 *
 *  RECEIVE binary             → raw PCM-16 audio at 24 kHz (play it)
 *  RECEIVE { type: "assistant_text", content }  → append to AI bubble
 *  RECEIVE { type: "user_text",      content }  → update user bubble
 *  RECEIVE { type: "turn_complete" }            → finalise bubbles
 *  RECEIVE { type: "interrupted"  }             → stop playback + reset
 *  RECEIVE { type: "error",        content }    → show error
 */

// ─── Config ──────────────────────────────────────────────────────────
const WS_URL = "ws://localhost:8765";

// ─── DOM refs ────────────────────────────────────────────────────────
const statusPill     = document.getElementById("statusPill");
const statusDot      = document.getElementById("statusDot");
const statusText     = document.getElementById("statusText");
const connectBtn     = document.getElementById("connectBtn");
const disconnectBtn  = document.getElementById("disconnectBtn");
const chatLog        = document.getElementById("chatLog");
const emptyState     = document.getElementById("emptyState");
const textInput      = document.getElementById("textInput");
const sendBtn        = document.getElementById("sendBtn");
const micBtn         = document.getElementById("micBtn");
const micIconOn      = document.getElementById("micIconOn");
const micIconOff     = document.getElementById("micIconOff");

// ─── State ───────────────────────────────────────────────────────────
let ws                  = null;
let audioCtx            = null;
let nextAudioStart      = 0;          // scheduled play-cursor
let currentUserBubble   = null;       // DOM node being streamed into
let currentAIBubble     = null;       // DOM node being streamed into
const RECEIVE_SAMPLE_RATE = 24000;

// ─── Mic state ───────────────────────────────────────────────────────
let micStream           = null;       // MediaStream from getUserMedia
let micSource           = null;       // MediaStreamAudioSourceNode
let micProcessor        = null;       // AudioWorkletNode
let micAudioCtx         = null;       // separate AudioContext for capture
let micActive           = false;
let dummyGain           = null;       // Gain node to prevent feedback
const SEND_SAMPLE_RATE  = 16000;      // Gemini expects 16kHz PCM-16

// ─── Audio helpers ───────────────────────────────────────────────────

/** Lazily create / resume the Web Audio context (requires user gesture). */
function ensureAudioCtx() {
  if (!audioCtx) {
    audioCtx   = new (window.AudioContext || window.webkitAudioContext)();
    nextAudioStart = 0;
  }
  if (audioCtx.state === "suspended") audioCtx.resume();
}

/**
 * Schedule an ArrayBuffer of raw PCM-Int16 @ 24 kHz for gapless playback.
 * Chunks are queued back-to-back so Gemini's streamed audio sounds seamless.
 */
function scheduleAudioChunk(arrayBuffer) {
  ensureAudioCtx();

  const pcm16    = new Int16Array(arrayBuffer);
  const float32  = new Float32Array(pcm16.length);
  for (let i = 0; i < pcm16.length; i++) {
    float32[i] = pcm16[i] / 32768.0;
  }

  const audioBuffer = audioCtx.createBuffer(1, float32.length, RECEIVE_SAMPLE_RATE);
  audioBuffer.getChannelData(0).set(float32);

  const source = audioCtx.createBufferSource();
  source.buffer = audioBuffer;
  source.connect(audioCtx.destination);

  const now    = audioCtx.currentTime;
  nextAudioStart = Math.max(now, nextAudioStart);
  source.start(nextAudioStart);
  nextAudioStart += audioBuffer.duration;
}

/** Stop any buffered audio immediately (called on interruption). */
function stopAudio() {
  if (audioCtx) {
    // Easiest atomic stop: close + null so the next chunk rebuilds
    audioCtx.close();
    audioCtx       = null;
    nextAudioStart = 0;
  }
}

// ─── Microphone capture (AudioWorklet) ───────────────────────────────

/** Start capturing mic audio and streaming PCM-16 chunks to the server. */
async function startMic() {
  if (micActive) return;
  try {
    micStream = await navigator.mediaDevices.getUserMedia({ audio: true, video: false });
    micAudioCtx = new (window.AudioContext || window.webkitAudioContext)();
    micSource   = micAudioCtx.createMediaStreamSource(micStream);

    // 1. Load the Worklet file (the secondary thread)
    await micAudioCtx.audioWorklet.addModule('./audio-processor.js');

    // 2. Create the Worklet node passing the current microphone sample rate
    micProcessor = new AudioWorkletNode(micAudioCtx, 'pcm-processor', {
      processorOptions: { sampleRate: micAudioCtx.sampleRate }
    });

    // 3. Listen for messages (ready audio packets) from the secondary thread
    micProcessor.port.onmessage = (evt) => {
      if (!micActive || !ws || ws.readyState !== WebSocket.OPEN) return;
      // evt.data contains the 16kHz Int16 ArrayBuffer ready to be sent
      ws.send(evt.data);
    };

    // 4. Connect the nodes
    micSource.connect(micProcessor);
    
    // Trick: to keep the processor alive on all browsers, we must connect it
    // to the final destination, but route it through a "Gain" at 0 volume to prevent echo.
    dummyGain = micAudioCtx.createGain();
    dummyGain.gain.value = 0;
    micProcessor.connect(dummyGain);
    dummyGain.connect(micAudioCtx.destination);

    micActive = true;
    micBtn.classList.add("active");
    micIconOn.style.display  = "none";
    micIconOff.style.display = "";
    micBtn.title = "Stop microphone";
    console.log("[Mic] AudioWorklet started — browser SR:", micAudioCtx.sampleRate, "→ sending at", SEND_SAMPLE_RATE);
  } catch (err) {
    console.error("[Mic] getUserMedia failed:", err);
    alert("Microphone access denied or unavailable: " + err.message);
  }
}

/** Stop mic capture and free resources. */
function stopMic() {
  if (!micActive) return;
  micActive = false;
  
  if (micProcessor) { 
    micProcessor.disconnect(); 
    micProcessor = null; 
  }
  if (dummyGain) {
    dummyGain.disconnect();
    dummyGain = null;
  }
  if (micSource) { 
    micSource.disconnect(); 
    micSource = null; 
  }
  if (micStream) { 
    micStream.getTracks().forEach(t => t.stop()); 
    micStream = null; 
  }
  if (micAudioCtx) { 
    micAudioCtx.close(); 
    micAudioCtx = null; 
  }
  
  micBtn.classList.remove("active");
  micIconOn.style.display  = "";
  micIconOff.style.display = "none";
  micBtn.title = "Toggle microphone";
  console.log("[Mic] Stopped.");

  // Send turn_complete signal to Gemini so it knows the user finished speaking
  if (ws && ws.readyState === WebSocket.OPEN) {
    ws.send(JSON.stringify({ type: "audio_end" }));
    console.log("[Mic] Sent audio_end signal");
  }
}

// ─── UI helpers ──────────────────────────────────────────────────────

function setStatus(state) {
  // state: "disconnected" | "connecting" | "connected" | "error"
  statusPill.className = `status-pill ${state}`;
  const labels = {
    disconnected: "Disconnected",
    connecting:   "Connecting…",
    connected:    "Connected",
    error:        "Error",
  };
  statusText.textContent = labels[state] ?? state;
}

function setConnectedUI(connected) {
  connectBtn.style.display    = connected ? "none"         : "";
  disconnectBtn.style.display = connected ? ""             : "none";
  textInput.disabled          = !connected;
  sendBtn.disabled            = !connected;
  micBtn.disabled             = !connected;
  if (!connected) stopMic();
  if (connected) textInput.focus();
}

function hideEmptyState() {
  if (emptyState) emptyState.style.display = "none";
}

/**
 * Create a new message row (user | assistant) and append it to the chat log.
 * Returns the inner bubble <div> so callers can stream text into it.
 */
function createMessageRow(role) {
  hideEmptyState();

  const row    = document.createElement("div");
  row.className = `message-row ${role}`;

  const avatar = document.createElement("div");
  avatar.className = "message-avatar";
  avatar.textContent = role === "user" ? "U" : "✦";

  const bubble = document.createElement("div");
  bubble.className = "message-bubble";

  row.appendChild(avatar);
  row.appendChild(bubble);
  chatLog.appendChild(row);
  chatLog.scrollTop = chatLog.scrollHeight;
  return bubble;
}

/** Append text to an existing bubble, or create a new one if needed. */
function appendToBubble(bubbleRef, text, role) {
  if (!bubbleRef) {
    bubbleRef = createMessageRow(role);
  }
  bubbleRef.textContent += text;
  chatLog.scrollTop = chatLog.scrollHeight;
  return bubbleRef;
}

/** Show a transient "typing…" indicator while waiting for AI response. */
function showTypingIndicator() {
  removeTypingIndicator();
  const row    = document.createElement("div");
  row.id       = "typingRow";
  row.className = "message-row assistant";

  const avatar = document.createElement("div");
  avatar.className = "message-avatar";
  avatar.textContent = "G";

  const bubble = document.createElement("div");
  bubble.className = "message-bubble typing-bubble";
  bubble.innerHTML  = "<span></span><span></span><span></span>";

  row.appendChild(avatar);
  row.appendChild(bubble);
  chatLog.appendChild(row);
  chatLog.scrollTop = chatLog.scrollHeight;
}

function removeTypingIndicator() {
  const el = document.getElementById("typingRow");
  if (el) el.remove();
}

// ─── WebSocket ───────────────────────────────────────────────────────

function connect() {
  setStatus("connecting");
  connectBtn.disabled = true;

  ws = new WebSocket(WS_URL);
  ws.binaryType = "arraybuffer";

  ws.onopen = () => {
    setStatus("connected");
    setConnectedUI(true);
    connectBtn.disabled = false;
    currentUserBubble = null;
    currentAIBubble   = null;

    // Show empty line and timestamp when connection starts
    hideEmptyState();
    
    // Empty line
    const emptyRow = document.createElement("div");
    emptyRow.className = "timestamp-row";
    emptyRow.innerHTML = "&nbsp;";
    chatLog.appendChild(emptyRow);
    
    // Timestamp
    const now = new Date();
    const timestampRow = document.createElement("div");
    timestampRow.className = "timestamp-row";
    const timestampText = document.createElement("span");
    timestampText.className = "timestamp-text";
    timestampText.textContent = now.toLocaleString();
    timestampRow.appendChild(timestampText);
    chatLog.appendChild(timestampRow);
    
    chatLog.scrollTop = chatLog.scrollHeight;
  };

  ws.onmessage = (event) => {
    if (event.data instanceof ArrayBuffer) {
      // Binary → audio chunk
      removeTypingIndicator();
      scheduleAudioChunk(event.data);
    } else {
      // JSON control message
      try {
        handleJsonMessage(JSON.parse(event.data));
      } catch (e) {
        console.error("JSON parse error:", e);
      }
    }
  };

  ws.onclose = () => {
    setStatus("disconnected");
    setConnectedUI(false);
    connectBtn.disabled = false;
    ws = null;
    removeTypingIndicator();
    stopAudio();
  };

  ws.onerror = (e) => {
    console.error("WebSocket error:", e);
    setStatus("error");
    connectBtn.disabled = false;
  };
}

function disconnect() {
  if (ws) {
    ws.close();
    ws = null;
  }
  stopAudio();
  removeTypingIndicator();
  setStatus("disconnected");
  setConnectedUI(false);
}

// ─── Incoming message handler ────────────────────────────────────────

function handleJsonMessage(msg) {
  switch (msg.type) {

    case "assistant_text":
      removeTypingIndicator();
      currentAIBubble = appendToBubble(currentAIBubble, msg.content, "assistant");
      break;

    case "user_text":
      // Transcription of the user's spoken audio
      currentUserBubble = appendToBubble(currentUserBubble, msg.content, "user");
      break;

    case "turn_complete":
      currentAIBubble   = null;
      currentUserBubble = null;
      break;

    case "interrupted":
      stopAudio();
      currentAIBubble   = null;
      currentUserBubble = null;
      removeTypingIndicator();
      break;

    case "error":
      removeTypingIndicator();
      console.error("Bridge error:", msg.content);
      setStatus("error");
      statusText.textContent = "Error: " + (msg.content ?? "unknown");
      break;
  }
}

// ─── Sending text ────────────────────────────────────────────────────

function sendText() {
  const text = textInput.value.trim();
  if (!text || !ws || ws.readyState !== WebSocket.OPEN) return;

  // Optimistically show the user message immediately
  currentUserBubble = createMessageRow("user");
  currentUserBubble.textContent = text;
  currentUserBubble = null;   // don't accumulate more into it

  // Show typing indicator while waiting
  showTypingIndicator();
  currentAIBubble = null;

  ws.send(JSON.stringify({ type: "text", content: text }));
  textInput.value = "";
}

// ─── Event listeners ─────────────────────────────────────────────────

connectBtn.addEventListener("click", connect);
disconnectBtn.addEventListener("click", disconnect);
sendBtn.addEventListener("click", sendText);
textInput.addEventListener("keydown", (e) => {
  if (e.key === "Enter" && !e.shiftKey) {
    e.preventDefault();
    sendText();
  }
});

/** Mic button: toggle capture on/off. */
micBtn.addEventListener("click", () => {
  if (micActive) {
    stopMic();
  } else {
    startMic();
  }
});