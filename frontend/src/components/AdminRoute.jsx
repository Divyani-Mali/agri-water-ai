import { Navigate, Outlet } from "react-router-dom";
import { useAuth } from "../context/authContext";

// Farmers who type /admin in the address bar are sent back to the farms page.
export default function AdminRoute() {
  const { user } = useAuth();
  return user?.role === "admin" ? <Outlet /> : <Navigate to="/" replace />;
}
