import type { Transcription } from "../../types/transcription";

interface TranscriptionItemProps {
  transcription: Transcription;
}

export function TranscriptionItem({ transcription }: TranscriptionItemProps) {
  return (
    <article className="rounded-md border border-line bg-panel-alt px-4 py-3">
      <h3 className="text-sm text-text-primary">{transcription.title}</h3>
    </article>
  );
}
