import { Link, Outlet } from "react-router-dom";
import { useAuth } from "../context/authContext";

export default function Layout() {
  const { user, logout } = useAuth();

  return (
    <div className="min-h-screen bg-gray-50">
      <header className="bg-green-700 text-white shadow">
        <div className="mx-auto flex max-w-6xl items-center justify-between px-4 py-3">
          <Link to="/" className="text-lg font-bold">
            💧 Smart Irrigation AI
          </Link>
          <div className="flex items-center gap-4 text-sm">
            <span>{user.full_name}</span>
            <span className="rounded-full bg-green-900 px-2 py-0.5 text-xs uppercase">
              {user.role}
            </span>
            <button
              onClick={logout}
              className="rounded bg-white/20 px-3 py-1 hover:bg-white/30"
            >
              Logout
            </button>
          </div>
        </div>
      </header>
      <main className="mx-auto max-w-6xl px-4 py-6">
        <Outlet />
      </main>
    </div>
  );
}
