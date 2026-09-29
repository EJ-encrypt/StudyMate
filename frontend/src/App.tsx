import { Navigate, Route, Routes, useLocation } from "react-router-dom";

import Nav from "./components/Nav";
import ProtectedRoute from "./components/ProtectedRoute";
import { useAuth } from "./context/AuthContext";
import Coach from "./pages/Coach";
import ConceptDetail from "./pages/ConceptDetail";
import CourseDetail from "./pages/CourseDetail";
import Login from "./pages/Login";
import MyCourses from "./pages/MyCourses";
import Onboarding from "./pages/Onboarding";
import Profile from "./pages/Profile";
import Quiz from "./pages/Quiz";
import Register from "./pages/Register";
import StudyEngine from "./pages/StudyEngine";
import StudyCourse from "./pages/StudyCourse";

/** Sends a signed-in student who has not set their school through onboarding. */
function RequireOnboarding() {
  const { user } = useAuth();
  const location = useLocation();

  if (user && !user.school && location.pathname !== "/welcome") {
    return <Navigate to="/welcome" replace />;
  }
  return null;
}

export default function App() {
  const { user } = useAuth();

  return (
    <div className="flex min-h-screen bg-slate-50">
      <Nav />
      <div className="min-w-0 flex-1">
        <RequireOnboarding />
        <main className={user ? "mx-auto max-w-5xl px-5 py-5" : ""}>
          <Routes>
            <Route path="/login" element={<Login />} />
            <Route path="/register" element={<Register />} />
            <Route element={<ProtectedRoute />}>
              <Route path="/welcome" element={<Onboarding />} />
              <Route path="/courses" element={<MyCourses />} />
              <Route path="/courses/:courseId" element={<CourseDetail />} />
              <Route path="/study" element={<StudyEngine />} />
              <Route path="/study/:courseId" element={<StudyCourse />} />
              <Route path="/coach" element={<Coach />} />
              <Route path="/coach/concept/:conceptId" element={<ConceptDetail />} />
              <Route path="/profile" element={<Profile />} />
              <Route path="/quiz/:assessmentId" element={<Quiz />} />
            </Route>
            <Route path="/" element={<Navigate to="/courses" replace />} />
          </Routes>
        </main>
      </div>
    </div>
  );
}
