/**
 * vad-processor.js
 * AudioWorklet processor — runs on audio thread
 * Computes RMS energy and sends PCM chunks to main thread
 */
class VADProcessor extends AudioWorkletProcessor {
  constructor() {
    super();
    this._buffer = [];
    this._frameSize = 160; // 10ms at 16kHz
    this._energyHistory = [];
    this._threshold = 0.015;
    this._smoothed = 0;
  }

  process(inputs) {
    const input = inputs[0];
    if (!input || !input[0]) return true;

    const samples = input[0]; // Float32Array

    // Resample to 16kHz if needed (assuming 44.1k or 48k → 16k)
    const resampled = this._resampleTo16k(samples);

    // Convert Float32 → Int16 PCM
    const pcm = new Int16Array(resampled.length);
    for (let i = 0; i < resampled.length; i++) {
      pcm[i] = Math.max(-32768, Math.min(32767, resampled[i] * 32768));
    }

    // Compute RMS energy
    let sumSq = 0;
    for (let i = 0; i < samples.length; i++) sumSq += samples[i] * samples[i];
    const rms = Math.sqrt(sumSq / samples.length);

    // Smooth energy
    this._smoothed = this._smoothed * 0.85 + rms * 0.15;

    // VAD decision
    const isSpeech = this._smoothed > this._threshold;

    // Send chunk to main thread
    this.port.postMessage({
      type: 'chunk',
      pcm: pcm.buffer,
      rms: this._smoothed,
      is_speech: isSpeech,
    }, [pcm.buffer]);

    return true;
  }

  _resampleTo16k(samples) {
    const inputRate = sampleRate; // AudioWorkletGlobalScope.sampleRate
    if (inputRate === 16000) return samples;
    const ratio = inputRate / 16000;
    const outLen = Math.floor(samples.length / ratio);
    const out = new Float32Array(outLen);
    for (let i = 0; i < outLen; i++) {
      out[i] = samples[Math.floor(i * ratio)];
    }
    return out;
  }
}

registerProcessor('vad-processor', VADProcessor);