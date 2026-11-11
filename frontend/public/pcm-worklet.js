// Converts microphone audio to 16 kHz mono 16-bit PCM for Deepgram.
// Posts { pcm: ArrayBuffer, rms: number } every 50 ms of audio.

const TARGET_RATE = 16000;
const CHUNK_SAMPLES = 800; // 50 ms at 16 kHz

class PcmCapture extends AudioWorkletProcessor {
  constructor() {
    super();
    this.ratio = sampleRate / TARGET_RATE;
    this.phase = 0;
    this.acc = 0;
    this.accCount = 0;
    this.out = new Int16Array(CHUNK_SAMPLES);
    this.outIndex = 0;
    this.sumSquares = 0;
  }

  process(inputs) {
    const channel = inputs[0] && inputs[0][0];
    if (!channel) return true;

    for (let i = 0; i < channel.length; i++) {
      // Average the input samples that fall into each output sample.
      this.acc += channel[i];
      this.accCount += 1;
      this.phase += 1;
      if (this.phase < this.ratio) continue;
      this.phase -= this.ratio;

      const sample = Math.max(-1, Math.min(1, this.acc / this.accCount));
      this.acc = 0;
      this.accCount = 0;
      this.out[this.outIndex++] = sample < 0 ? sample * 0x8000 : sample * 0x7fff;
      this.sumSquares += sample * sample;

      if (this.outIndex === CHUNK_SAMPLES) {
        const rms = Math.sqrt(this.sumSquares / CHUNK_SAMPLES);
        this.port.postMessage({ pcm: this.out.buffer, rms }, [this.out.buffer]);
        this.out = new Int16Array(CHUNK_SAMPLES);
        this.outIndex = 0;
        this.sumSquares = 0;
      }
    }
    return true;
  }
}

registerProcessor("pcm-capture", PcmCapture);
