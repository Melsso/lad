import { AppLayout } from "../components/layout/AppLayout";

export function TranscriptionPage() {
  return (
    <AppLayout>
      <div className="flex h-full flex-col items-center justify-center gap-2 px-8 text-center">
        <h2 className="font-display text-2xl font-semibold tracking-wide text-text-primary">
          Transcriptions
        </h2>
        <p className="max-w-sm font-mono text-xs text-text-dim">
          transcription module not yet online.
        </p>
      </div>
    </AppLayout>
  );
}
