import { Navigate, Route, Routes } from "react-router-dom";

import { ChatPage } from "./pages/ChatPage";
import { TranscriptionPage } from "./pages/TranscriptionPage";

function App() {
  return (
    <Routes>
      <Route path="/" element={<Navigate to="/chat" replace />} />

      <Route path="/chat" element={<ChatPage />} />

      <Route path="/chat/:chatId" element={<ChatPage />} />

      <Route path="/transcriptions" element={<TranscriptionPage />} />

      <Route
        path="/transcriptions/:transcriptionId"
        element={<TranscriptionPage />}
      />
    </Routes>
  );
}

export default App;
