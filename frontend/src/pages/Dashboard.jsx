import { useEffect, useState } from "react";
import api, { errorMessage } from "../api/client";
import { useAuth } from "../context/authContext";

export default function Dashboard() {
  const { user } = useAuth();
  const [farms, setFarms] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    api
      .get("/api/farms")
      .then((res) => setFarms(res.data))
      .catch((err) => setError(errorMessage(err)))
      .finally(() => setLoading(false));
  }, []);

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-800">
          Welcome, {user.full_name} 👋
        </h1>
        <p className="text-sm text-gray-500">
          Here is an overview of your farms.
        </p>
      </div>

      {error && (
        <div className="rounded bg-red-50 p-3 text-sm text-red-700">
          {error}
        </div>
      )}

      <div className="rounded-xl bg-white p-5 shadow">
        <h2 className="mb-3 font-semibold text-gray-700">
          Your farms {loading ? "" : `(${farms.length})`}
        </h2>

        {loading && <p className="text-gray-500">Loading...</p>}

        {!loading && farms.length === 0 && (
          <p className="text-gray-500">
            No farms yet. We will add farms in the next phase.
          </p>
        )}

        <ul className="divide-y">
          {farms.map((farm) => (
            <li key={farm.id} className="py-3">
              <p className="font-medium">{farm.name}</p>
              <p className="text-sm text-gray-500">{farm.location}</p>
            </li>
          ))}
        </ul>
      </div>
    </div>
  );
}
