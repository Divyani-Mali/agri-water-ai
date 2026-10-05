import { Navigate, Outlet } from "react-router-dom";
import { useAuth } from "../context/authContext";

export default function ProtectedRoute() {
  const { user, loading } = useAuth();

  if (loading) {
    return <div className="p-10 text-center text-gray-500">Loading...</div>;
  }
  return user ? <Outlet /> : <Navigate to="/login" replace />;
}
