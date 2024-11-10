import SpeechMetrics from './SpeechMetrics';

export default class TranscriptionHandler {
    private metrics: SpeechMetrics;
    private lastPrintedWords: Set<string>;

    constructor() {
        this.metrics = new SpeechMetrics();
        this.lastPrintedWords = new Set();
    }

    async handleTranscriptEvent(transcriptEvent: any): Promise<void> {
        const results = transcriptEvent.transcript.results;

        for (const result of results) {
            for (const alt of result.alternatives) {
                const words = alt.transcript.trim().split(' ');
                const currentWords = new Set(words);

                this.metrics.addWords(alt.transcript);

                const newWords = new Set([...currentWords].filter((x) => !this.lastPrintedWords.has(x)));
                words.forEach((word) => {
                    if (newWords.has(word)) {
                        console.log(word);
                    }
                });

                this.lastPrintedWords = result.isPartial ? currentWords : new Set();
            }
        }
    }

    getMetrics() {
        return {
            speechRate: this.metrics.getSpeechRate(),
            fillerPercentage: this.metrics.getFillerPercentage(),
        };
    }
}
