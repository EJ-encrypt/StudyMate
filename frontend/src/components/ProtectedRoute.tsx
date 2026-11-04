import { Navigate, Outlet, useLocation } from "react-router-dom";

import { useAuth } from "../context/AuthContext";
import { ListSkeleton } from "./ui";

export default function ProtectedRoute() {
  const { user, isLoading } = useAuth();
  const location = useLocation();

  if (isLoading) {
    return (
      <div className="mx-auto max-w-3xl p-4 sm:p-8">
        <ListSkeleton rows={3} />
      </div>
    );
  }

  if (!user) {
    // Remember where they were going, e.g. a reminder link to a reflection.
    return <Navigate to="/login" replace state={{ from: location.pathname }} />;
  }

  return <Outlet />;
}
