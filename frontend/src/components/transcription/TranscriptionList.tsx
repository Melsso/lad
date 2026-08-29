import { Link } from "react-router-dom";

export function TranscriptionList() {
  return (
    <section>
      <div className="mb-3 flex items-center justify-between">
        <h2 className="font-mono text-xs tracking-[0.2em] text-text-dim uppercase">
          Transcriptions
        </h2>

        <span className="flex h-6 w-6 items-center justify-center rounded border border-line text-text-dim">
          +
        </span>
      </div>

      <p className="font-mono text-xs text-text-dim">no transcriptions yet.</p>

      <Link
        to="/transcriptions"
        className="mt-1 inline-block font-mono text-xs text-cyan hover:underline"
      >
        view all
      </Link>
    </section>
  );
}
