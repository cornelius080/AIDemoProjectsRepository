/**
 * audio-processor.js
 * 
 * Runs in a separate thread (AudioWorklet).
 * Captures audio, downsamples it to 16kHz, and converts it to 16-bit PCM.
 */

class PCMProcessor extends AudioWorkletProcessor {
    /**
     * Initializes the PCM Audio Processor.
     * 
     * @param {Object} options Configuration options passed into the processor.
     */
    constructor(options) {
        super();
        
        // Browser microphone sample rate (e.g., 44100 or 48000 Hz)
        this.inRate = options.processorOptions.sampleRate || 48000;
        
        // Sample rate expected by Gemini output
        this.outRate = 16000;
        
        // Accumulate 4096 frames before sending a chunk to the main thread
        this.chunkSize = 4096; 
        this.buffer = new Float32Array(this.chunkSize);
        this.frames = 0;
    }

    /**
     * Processing function that gets called continuously to chunk data.
     * 
     * @param {Array} inputs A given input array buffer collection.
     * @param {Array} outputs Expected layout target arrays (not used).
     * @param {Object} parameters Additional parameters supplied via configs.
     * @returns {boolean} Should always return true to stay alive.
     */
    process(inputs, outputs, parameters) {
        const input = inputs[0];
        if (!input || !input[0]) {
            return true;
        }
        
        const channel = input[0];

        // Accumulate audio sample data sequentially
        for (let i = 0; i < channel.length; i++) {
            this.buffer[this.frames++] = channel[i];
            
            // Reached our chunk capacity logic point, flush buffer contents
            if (this.frames >= this.chunkSize) {
                this.flush();
            }
        }
        
        // Return true to keep the processor thread alive
        return true; 
    }

    /**
     * Resamples and dispatches audio buffers array frame chunk to the main thread.
     */
    flush() {
        const ratio = this.inRate / this.outRate;
        const newLen = Math.round(this.chunkSize / ratio);
        const int16 = new Int16Array(newLen);

        // Basic downsampling via block average logic plus conversion to 16-bit Int
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
            // Bound convert array from Float32 (-1.0 to 1.0) into Int16 limits
            int16[i] = Math.max(-32768, Math.min(32767, Math.round(avg * 32767)));
            offset = nextOffset;
        }

        // Send binary data using Zero-copy transfer mechanism for performance
        this.port.postMessage(int16.buffer, [int16.buffer]);

        // Reset buffer frames variable counts
        this.frames = 0;
        this.buffer = new Float32Array(this.chunkSize);
    }
}

// Global scope registration call handling logic link
registerProcessor('pcm-processor', PCMProcessor);