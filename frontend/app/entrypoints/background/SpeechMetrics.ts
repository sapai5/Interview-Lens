export interface FillerWords {
  [key: string]: number;
  um: number;
  uh: number;
  er: number;
  ah: number;
  like: number;
  'you know': number;
  'sort of': number;
  'kind of': number;
}

export default class SpeechMetrics {
  private fillerWords: FillerWords;
  private totalWords: number;
  private readonly windowSeconds: number;
  private wordTimestamps: number[];

  constructor(windowSeconds: number = 60) {
      this.fillerWords = {
          um: 0,
          uh: 0,
          er: 0,
          ah: 0,
          like: 0,
          'you know': 0,
          'sort of': 0,
          'kind of': 0,
      };
      this.totalWords = 0;
      this.windowSeconds = windowSeconds;
      this.wordTimestamps = [];
  }

  addWords(text: string): void {
      const currentTime = Date.now() / 1000;
      const words = text.toLowerCase().split(' ');

      this.totalWords += words.length;

      words.forEach(() => this.wordTimestamps.push(currentTime));

      while (this.wordTimestamps.length > 0 && currentTime - this.wordTimestamps[0] > this.windowSeconds) {
          this.wordTimestamps.shift();
      }

      Object.keys(this.fillerWords).forEach((filler) => {
          const regex = new RegExp(`\\b${filler}\\b`, 'gi');
          this.fillerWords[filler] += (text.toLowerCase().match(regex) || []).length;
      });
  }

  getSpeechRate(): number {
      if (this.wordTimestamps.length === 0) return 0;

      const currentTime = Date.now() / 1000;
      const windowWords = this.wordTimestamps.filter((t) => currentTime - t <= this.windowSeconds).length;
      const minutes = this.windowSeconds / 60;

      return minutes > 0 ? (windowWords / minutes) : 0;
  }

  getFillerPercentage(): number {
      const totalFillers = Object.values(this.fillerWords).reduce((a, b) => a + b, 0);
      return this.totalWords > 0 ? (totalFillers / this.totalWords) * 100 : 0;
  }
}
