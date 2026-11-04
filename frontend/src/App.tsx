import { Navigate, Route, Routes, useLocation } from "react-router-dom";

import { MobileHeader, Sidebar, TabBar } from "./components/Nav";
import ProtectedRoute from "./components/ProtectedRoute";
import Tutorial from "./components/Tutorial";
import { useAuth } from "./context/AuthContext";
import Arcade from "./pages/Arcade";
import BeatTheClock from "./pages/BeatTheClock";
import Coach from "./pages/Coach";
import ConceptDetail from "./pages/ConceptDetail";
import ConceptMatch from "./pages/ConceptMatch";
import CourseDetail from "./pages/CourseDetail";
import Friends from "./pages/Friends";
import Login from "./pages/Login";
import MyCourses from "./pages/MyCourses";
import OddOneOut from "./pages/OddOneOut";
import Onboarding from "./pages/Onboarding";
import Profile from "./pages/Profile";
import Quiz from "./pages/Quiz";
import Reflect from "./pages/Reflect";
import Register from "./pages/Register";
import ResetPassword from "./pages/ResetPassword";
import Schedule from "./pages/Schedule";
import Settings from "./pages/Settings";
import StudyEngine from "./pages/StudyEngine";
import StudyCourse from "./pages/StudyCourse";
import ThreeStrikes from "./pages/ThreeStrikes";
import TrueFalse from "./pages/TrueFalse";

/** Sends a signed-in student who has not set their school through onboarding. */
function RequireOnboarding() {
  const { user, isRecoveringPassword } = useAuth();
  const location = useLocation();

  if (isRecoveringPassword && location.pathname !== "/reset-password") {
    return <Navigate to="/reset-password" replace />;
  }
  if (user && !user.school && !["/welcome", "/reset-password"].includes(location.pathname)) {
    return <Navigate to="/welcome" replace />;
  }
  return null;
}

export default function App() {
  const { user } = useAuth();

  return (
    <div className="flex min-h-screen bg-canvas">
      <Tutorial />
      <Sidebar />
      <div className="min-w-0 flex-1">
        <MobileHeader />
        <RequireOnboarding />
        <main className={user ? "mx-auto max-w-5xl px-4 pb-24 pt-5 sm:px-6 md:pb-10 md:pt-8" : ""}>
          <Routes>
            <Route path="/login" element={<Login />} />
            <Route path="/register" element={<Register />} />
            <Route path="/reset-password" element={<ResetPassword />} />
            <Route element={<ProtectedRoute />}>
              <Route path="/welcome" element={<Onboarding />} />
              <Route path="/courses" element={<MyCourses />} />
              <Route path="/courses/:courseId" element={<CourseDetail />} />
              <Route path="/study" element={<StudyEngine />} />
              <Route path="/study/:courseId" element={<StudyCourse />} />
              <Route path="/play" element={<Arcade />} />
              <Route path="/play/:courseId/clock" element={<BeatTheClock />} />
              <Route path="/play/:courseId/match" element={<ConceptMatch />} />
              <Route path="/play/:courseId/blitz" element={<TrueFalse />} />
              <Route path="/play/:courseId/odd" element={<OddOneOut />} />
              <Route path="/play/:courseId/strikes" element={<ThreeStrikes />} />
              <Route path="/friends" element={<Friends />} />
              <Route path="/schedule" element={<Schedule />} />
              <Route path="/lectures/:slotId/reflect" element={<Reflect />} />
              <Route path="/coach" element={<Coach />} />
              <Route path="/coach/concept/:conceptId" element={<ConceptDetail />} />
              <Route path="/profile" element={<Profile />} />
              <Route path="/settings" element={<Settings />} />
              <Route path="/quiz/:assessmentId" element={<Quiz />} />
            </Route>
            <Route path="/" element={<Navigate to="/courses" replace />} />
            {/* Vercel serves index.html for any path, so an unknown URL has to
                land somewhere here rather than rendering an empty page. */}
            <Route path="*" element={<Navigate to="/courses" replace />} />
          </Routes>
        </main>
        <TabBar />
      </div>
    </div>
  );
}
