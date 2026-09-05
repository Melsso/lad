import { Navigate, Route, Routes } from "react-router-dom";

import { ChatPage } from "./pages/ChatPage";

function App() {
  return (
    <Routes>
      <Route path="/" element={<Navigate to="/chat" replace />} />

      <Route path="/chat" element={<ChatPage />} />

      <Route path="/chat/:chatId" element={<ChatPage />} />
    </Routes>
  );
}

export default App;
