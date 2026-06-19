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

// ====================================================================
// Configuration Config
// ====================================================================
const WS_URL = "ws://localhost:8000/ws";

// ====================================================================
// DOM references
// ====================================================================
const statusPill = document.getElementById("statusPill");
const statusDot = document.getElementById("statusDot");
const statusText = document.getElementById("statusText");
const connectBtn = document.getElementById("connectBtn");
const disconnectBtn = document.getElementById("disconnectBtn");
const chatLog = document.getElementById("chatLog");
const emptyState = document.getElementById("emptyState");
const textInput = document.getElementById("textInput");
const sendBtn = document.getElementById("sendBtn");
const micBtn = document.getElementById("micBtn");
const micIconOn = document.getElementById("micIconOn");
const micIconOff = document.getElementById("micIconOff");

// ====================================================================
// State variables
// ====================================================================
let ws = null;
let audioCtx = null;
let nextAudioStart = 0; // Scheduled play-cursor
let currentUserBubble = null; // DOM node being streamed into
let currentAIBubble = null; // DOM node being streamed into
const RECEIVE_SAMPLE_RATE = 24000;

// ====================================================================
// Microphone capture variables
// ====================================================================
let micStream = null; // MediaStream from getUserMedia
let micSource = null; // MediaStreamAudioSourceNode
let micProcessor = null; // AudioWorkletNode
let micAudioCtx = null; // Separate AudioContext for capture
let micActive = false;
let dummyGain = null; // Gain node to prevent feedback
const SEND_SAMPLE_RATE = 16000; // Gemini expects 16kHz PCM-16

// ====================================================================
// Audio helpers
// ====================================================================

/**
 * Lazily create or resume the Web Audio context (requires user gesture).
 */
function ensureAudioCtx() {
    if (!audioCtx) {
        audioCtx = new (window.AudioContext || window.webkitAudioContext)();
        nextAudioStart = 0;
    }
    if (audioCtx.state === "suspended") {
        audioCtx.resume();
    }
}

/**
 * Schedule an ArrayBuffer of raw PCM-Int16 @ 24 kHz for gapless playback.
 * Chunks are queued back-to-back so Gemini's streamed audio sounds seamless.
 *
 * @param {ArrayBuffer} arrayBuffer The binary audio content array data.
 */
function scheduleAudioChunk(arrayBuffer) {
    ensureAudioCtx();

    const pcm16 = new Int16Array(arrayBuffer);
    const float32 = new Float32Array(pcm16.length);
    for (let i = 0; i < pcm16.length; i++) {
        float32[i] = pcm16[i] / 32768.0;
    }

    const audioBuffer = audioCtx.createBuffer(1, float32.length, RECEIVE_SAMPLE_RATE);
    audioBuffer.getChannelData(0).set(float32);

    const source = audioCtx.createBufferSource();
    source.buffer = audioBuffer;
    source.connect(audioCtx.destination);

    const now = audioCtx.currentTime;
    nextAudioStart = Math.max(now, nextAudioStart);
    source.start(nextAudioStart);
    nextAudioStart += audioBuffer.duration;
}

/**
 * Stop any buffered audio immediately (called on interruption).
 */
function stopAudio() {
    if (audioCtx) {
        audioCtx.close();
        audioCtx = null;
        nextAudioStart = 0;
    }
}

// ====================================================================
// Microphone capture functionality
// ====================================================================

/**
 * Start capturing microphone audio and stream PCM-16 chunks to the socket.
 */
async function startMic() {
    if (micActive) {
        return;
    }
    try {
        micStream = await navigator.mediaDevices.getUserMedia({ audio: true, video: false });
        micAudioCtx = new (window.AudioContext || window.webkitAudioContext)();
        micSource = micAudioCtx.createMediaStreamSource(micStream);

        // Load the AudioWorklet logic file
        await micAudioCtx.audioWorklet.addModule('./audio-processor.js');

        // Setup the specific output stream settings payload logic nodes
        micProcessor = new AudioWorkletNode(micAudioCtx, 'pcm-processor', {
            processorOptions: { sampleRate: micAudioCtx.sampleRate }
        });

        // Register message event handling to ship payloads through active network sockets
        micProcessor.port.onmessage = (event) => {
            if (!micActive || !ws || ws.readyState !== WebSocket.OPEN) {
                return;
            }
            ws.send(event.data);
        };

        // Attach input connection objects into routing arrays
        micSource.connect(micProcessor);
        
        // Anti-echo protection buffer volume mapping via gain logic objects
        dummyGain = micAudioCtx.createGain();
        dummyGain.gain.value = 0;
        micProcessor.connect(dummyGain);
        dummyGain.connect(micAudioCtx.destination);

        micActive = true;
        micBtn.classList.add("active");
        micIconOn.style.display = "none";
        micIconOff.style.display = "";
        micBtn.title = "Stop microphone";
        console.log(`[Mic] AudioWorklet started — SR: ${micAudioCtx.sampleRate} → ${SEND_SAMPLE_RATE}`);
    } catch (error) {
        console.error("[Mic] Media acquisition capture error:", error);
        alert("Microphone capture disabled or disconnected.");
    }
}

/**
 * Disconnect microphone connections and clean processing threads.
 */
function stopMic() {
    if (!micActive) {
        return;
    }
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
        micStream.getTracks().forEach((track) => track.stop()); 
        micStream = null; 
    }
    if (micAudioCtx) { 
        micAudioCtx.close(); 
        micAudioCtx = null; 
    }
    
    micBtn.classList.remove("active");
    micIconOn.style.display = "";
    micIconOff.style.display = "none";
    micBtn.title = "Toggle microphone";
    console.log("[Mic] Interruption complete.");

    // Inform the server completion
    if (ws && ws.readyState === WebSocket.OPEN) {
        ws.send(JSON.stringify({ type: "audio_end" }));
        console.log("[Mic] Alerted end logic pipeline.");
    }
}

// ====================================================================
// User Interface UI interactions
// ====================================================================

/**
 * Configure display pills denoting background state connection contexts.
 * 
 * @param {string} state Target status phrase context string.
 */
function setStatus(state) {
    statusPill.className = `status-pill ${state}`;
    const labels = {
        disconnected: "Disconnected",
        connecting: "Connecting...",
        connected: "Connected",
        error: "Error",
    };
    statusText.textContent = labels[state] ?? state;
}

/**
 * Disable buttons mapped dynamically based on current live context settings.
 * 
 * @param {boolean} connected Boolean true false representation block.
 */
function setConnectedUI(connected) {
    connectBtn.style.display = connected ? "none" : "";
    disconnectBtn.style.display = connected ? "" : "none";
    textInput.disabled = !connected;
    sendBtn.disabled = !connected;
    micBtn.disabled = !connected;
    if (!connected) {
        stopMic();
    }
    if (connected) {
        textInput.focus();
    }
}

/**
 * Helper to remove default UI prompt empty screen instructions node.
 */
function hideEmptyState() {
    if (emptyState) {
        emptyState.style.display = "none";
    }
}

/**
 * Append chat node element instances corresponding specifically user or bot.
 * 
 * @param {string} role Source identifier logic user bot block map.
 * @returns {HTMLElement} A configured reference wrapper row target.
 */
function createMessageRow(role) {
    hideEmptyState();

    const row = document.createElement("div");
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

/**
 * Apply chunk characters onto pre-created chat node elements.
 * 
 * @param {HTMLElement} bubbleRef Target row DOM structure.
 * @param {string} text Incoming raw text chunks strings.
 * @param {string} role Associated user role assignment identifier.
 * @returns {HTMLElement} Refreshed or generated node result references.
 */
function appendToBubble(bubbleRef, text, role) {
    if (!bubbleRef) {
        bubbleRef = createMessageRow(role);
    }
    bubbleRef.textContent += text;
    chatLog.scrollTop = chatLog.scrollHeight;
    return bubbleRef;
}

/**
 * Provide simulated animated graphics mimicking remote generation processing states.
 */
function showTypingIndicator() {
    removeTypingIndicator();
    const row = document.createElement("div");
    row.id = "typingRow";
    row.className = "message-row assistant";

    const avatar = document.createElement("div");
    avatar.className = "message-avatar";
    avatar.textContent = "G";

    const bubble = document.createElement("div");
    bubble.className = "message-bubble typing-bubble";
    bubble.innerHTML = "<span></span><span></span><span></span>";

    row.appendChild(avatar);
    row.appendChild(bubble);
    chatLog.appendChild(row);
    chatLog.scrollTop = chatLog.scrollHeight;
}

/**
 * Destroy the animated typing visual box.
 */
function removeTypingIndicator() {
    const targetElement = document.getElementById("typingRow");
    if (targetElement) {
        targetElement.remove();
    }
}

// ====================================================================
// Networking WebSockets implementations
// ====================================================================

/**
 * Initializes and wires local interactions targeting python APIs context links.
 */
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
        currentAIBubble = null;

        hideEmptyState();
        
        const emptyRow = document.createElement("div");
        emptyRow.className = "timestamp-row";
        emptyRow.innerHTML = "&nbsp;";
        chatLog.appendChild(emptyRow);
        
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
            removeTypingIndicator();
            scheduleAudioChunk(event.data);
        } else {
            try {
                handleJsonMessage(JSON.parse(event.data));
            } catch (error) {
                console.error("JSON extraction error parsing:", error);
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

    ws.onerror = (error) => {
        console.error("Transmission connection failure:", error);
        setStatus("error");
        connectBtn.disabled = false;
    };
}

/**
 * Close current socket routing instances deliberately.
 */
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

// ====================================================================
// Payload processor logic mapping routing
// ====================================================================

/**
 * Handle incoming JSON mapping control protocols correctly.
 * 
 * @param {Object} message Deserialized block of data dictionaries.
 */
function handleJsonMessage(message) {
    switch (message.type) {
        case "assistant_text":
            removeTypingIndicator();
            currentAIBubble = appendToBubble(currentAIBubble, message.content, "assistant");
            break;

        case "user_text":
            currentUserBubble = appendToBubble(currentUserBubble, message.content, "user");
            break;

        case "turn_complete":
            currentAIBubble = null;
            currentUserBubble = null;
            break;

        case "interrupted":
            stopAudio();
            currentAIBubble = null;
            currentUserBubble = null;
            removeTypingIndicator();
            break;

        case "error":
            removeTypingIndicator();
            console.error("Socket error processing pipeline:", message.content);
            setStatus("error");
            statusText.textContent = `Error: ${message.content || "unknown failure"}`;
            break;
    }
}

// ====================================================================
// Data dispatch mapping
// ====================================================================

/**
 * Evaluate box context info dispatch payload texts.
 */
function sendText() {
    const textData = textInput.value.trim();
    if (!textData || !ws || ws.readyState !== WebSocket.OPEN) {
        return;
    }

    currentUserBubble = createMessageRow("user");
    currentUserBubble.textContent = textData;
    currentUserBubble = null;

    showTypingIndicator();
    currentAIBubble = null;

    ws.send(JSON.stringify({ type: "text", content: textData }));
    textInput.value = "";
}

// ====================================================================
// Event Listeners registration assignment triggers
// ====================================================================

connectBtn.addEventListener("click", connect);
disconnectBtn.addEventListener("click", disconnect);
sendBtn.addEventListener("click", sendText);

textInput.addEventListener("keydown", (event) => {
    if (event.key === "Enter" && !event.shiftKey) {
        event.preventDefault();
        sendText();
    }
});

micBtn.addEventListener("click", () => {
    if (micActive) {
        stopMic();
    } else {
        startMic();
    }
});