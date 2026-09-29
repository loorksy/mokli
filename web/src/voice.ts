export type SpeechResult = { results: { 0: { 0: { transcript: string } } } };

export type SpeechRec = {
  lang: string;
  continuous: boolean;
  interimResults: boolean;
  start: () => void;
  stop: () => void;
  onresult: ((event: SpeechResult) => void) | null;
  onerror: (() => void) | null;
  onend: (() => void) | null;
};

export function recognition(): SpeechRec | null {
  const host = window as unknown as {
    SpeechRecognition?: new () => SpeechRec;
    webkitSpeechRecognition?: new () => SpeechRec;
  };
  const Ctor = host.SpeechRecognition || host.webkitSpeechRecognition;
  return Ctor ? new Ctor() : null;
}
