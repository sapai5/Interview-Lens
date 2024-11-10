export default class AudioCapture {
  private readonly sampleRate: number = 16000;
  private readonly chunkSize: number = 1024;
  private mediaStream: MediaStream | null = null;
  private audioContext: AudioContext | null = null;

  async initialize(): Promise<void> {
      try {
          this.mediaStream = await navigator.mediaDevices.getUserMedia({
              audio: {
                  sampleRate: this.sampleRate,
                  channelCount: 1,
                  echoCancellation: true,
                  noiseSuppression: true,
              },
          });

          this.audioContext = new AudioContext({ sampleRate: this.sampleRate });
      } catch (error) {
          console.error('Error initializing audio capture:', error);
          throw error;
      }
  }

  async startCapture(onAudioData: (data: Float32Array) => void): Promise<void> {
      if (!this.mediaStream || !this.audioContext) {
          throw new Error('Audio capture not initialized');
      }

      const source = this.audioContext.createMediaStreamSource(this.mediaStream);
      const processor = this.audioContext.createScriptProcessor(this.chunkSize, 1, 1);

      processor.onaudioprocess = (e: AudioProcessingEvent) => {
          const inputData = e.inputBuffer.getChannelData(0);
          onAudioData(inputData);
      };

      source.connect(processor);
      processor.connect(this.audioContext.destination);
  }

  stop(): void {
      if (this.mediaStream) {
          this.mediaStream.getTracks().forEach((track) => track.stop());
      }
      if (this.audioContext) {
          this.audioContext.close();
      }
  }
}
