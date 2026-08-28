import type { Transcription } from "../../types/transcription";

interface TranscriptionItemProps {
  transcription: Transcription;
}

export function TranscriptionItem({ transcription }: TranscriptionItemProps) {
  return (
    <article className="transcription-item">
      <h3>{transcription.title}</h3>
    </article>
  );
}
