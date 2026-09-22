import { Navigate, Route, Routes } from "react-router-dom";

import Nav from "./components/Nav";
import ProtectedRoute from "./components/ProtectedRoute";
import Coach from "./pages/Coach";
import Login from "./pages/Login";
import Materials from "./pages/Materials";
import Profile from "./pages/Profile";
import Register from "./pages/Register";
import Upload from "./pages/Upload";

export default function App() {
  return (
    <div className="min-h-screen bg-white">
      <Nav />
      <Routes>
        <Route path="/login" element={<Login />} />
        <Route path="/register" element={<Register />} />
        <Route element={<ProtectedRoute />}>
          <Route path="/upload" element={<Upload />} />
          <Route path="/materials" element={<Materials />} />
          <Route path="/coach" element={<Coach />} />
          <Route path="/profile" element={<Profile />} />
        </Route>
        <Route path="/" element={<Navigate to="/upload" replace />} />
      </Routes>
    </div>
  );
}
