import { Link } from "react-router-dom";

export function TranscriptionList() {
  return (
    <section className="transcription-list">
      <div className="sidebar-section-header">
        <h2>Transcriptions</h2>

        <button type="button">+</button>
      </div>

      <p>No transcriptions yet.</p>

      <Link to="/transcriptions">View all</Link>
    </section>
  );
}
