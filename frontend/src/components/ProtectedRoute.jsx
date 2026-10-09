import { Navigate, Outlet } from "react-router-dom";
import { useAuth } from "../context/authContext";
import { Spinner } from "./ui/Button";

export default function ProtectedRoute() {
  const { user, loading } = useAuth();

  if (loading) {
    return (
      <div className="flex min-h-screen items-center justify-center gap-3 text-ink-soft">
        <Spinner /> Restoring your session...
      </div>
    );
  }
  return user ? <Outlet /> : <Navigate to="/login" replace />;
}
