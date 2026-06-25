/**
 * audio-processor.js
 * Runs in a separate thread (AudioWorklet).
 * Captures audio, downsamples it to 16kHz, and converts it to 16-bit PCM.
 */

class PCMProcessor extends AudioWorkletProcessor {
  constructor(options) {
    super();
    // Browser microphone sample rate (e.g., 44100 or 48000 Hz)
    this.inRate = options.processorOptions.sampleRate || 48000;
    // Sample rate expected by Gemini
    this.outRate = 16000;
    
    // Accumulate 4096 frames before sending a chunk to the main thread
    this.chunkSize = 4096; 
    this.buffer = new Float32Array(this.chunkSize);
    this.frames = 0;
  }

  process(inputs, outputs, parameters) {
    const input = inputs[0];
    if (!input || !input[0]) return true;
    
    const channel = input[0];

    // Accumulate audio samples
    for (let i = 0; i < channel.length; i++) {
      this.buffer[this.frames++] = channel[i];
      if (this.frames >= this.chunkSize) {
        this.flush();
      }
    }
    
    // Return true to keep the processor alive
    return true; 
  }

  flush() {
    const ratio = this.inRate / this.outRate;
    const newLen = Math.round(this.chunkSize / ratio);
    const int16 = new Int16Array(newLen);

    // Basic downsampling (block average) + Conversion to 16-bit Int
    let offset = 0;
    for (let i = 0; i < newLen; i++) {
      const nextOffset = Math.round((i + 1) * ratio);
      let accum = 0;
      let count = 0;
      for (let j = offset; j < nextOffset && j < this.chunkSize; j++) {
        accum += this.buffer[j];
        count++;
      }
      const avg = count > 0 ? accum / count : 0;
      // Convert from Float32 (-1.0 to 1.0) to Int16 (-32768 to 32767)
      int16[i] = Math.max(-32768, Math.min(32767, Math.round(avg * 32767)));
      offset = nextOffset;
    }

    // Send binary data to the main thread (Zero-copy transfer for max performance)
    this.port.postMessage(int16.buffer, [int16.buffer]);

    // Reset the buffer for the next cycle
    this.frames = 0;
    this.buffer = new Float32Array(this.chunkSize);
  }
}

registerProcessor('pcm-processor', PCMProcessor);