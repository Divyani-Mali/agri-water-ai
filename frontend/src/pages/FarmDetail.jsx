import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import api, { errorMessage } from "../api/client";
import { CROPS, SOILS, cap, todayLocal } from "../constants";

export default function FarmDetail() {
  const { farmId } = useParams();
  const [farm, setFarm] = useState(null);
  const [fields, setFields] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [formError, setFormError] = useState("");
  const [showForm, setShowForm] = useState(false);
  const [saving, setSaving] = useState(false);
  const [version, setVersion] = useState(0);
  const [form, setForm] = useState({
    name: "",
    crop_type: "wheat",
    soil_type: "loamy",
    area_acres: "",
    planting_date: todayLocal(),
  });

  useEffect(() => {
    Promise.all([
      api.get(`/api/farms/${farmId}`),
      api.get(`/api/farms/${farmId}/fields`),
    ])
      .then(([farmRes, fieldsRes]) => {
        setFarm(farmRes.data);
        setFields(fieldsRes.data);
        setError("");
      })
      .catch((err) => setError(errorMessage(err)))
      .finally(() => setLoading(false));
  }, [farmId, version]);

  const reload = () => setVersion((v) => v + 1);
  const set = (key) => (e) => setForm({ ...form, [key]: e.target.value });

  const addField = async (e) => {
    e.preventDefault();
    setFormError("");
    if (!form.name.trim()) return setFormError("Please enter a field name");
    const area = Number(form.area_acres);
    if (!area || area <= 0) return setFormError("Area must be greater than 0");
    if (form.planting_date > todayLocal())
      return setFormError("Planting date cannot be in the future");

    setSaving(true);
    try {
      await api.post(`/api/farms/${farmId}/fields`, {
        name: form.name.trim(),
        crop_type: form.crop_type,
        soil_type: form.soil_type,
        area_acres: area,
        planting_date: form.planting_date,
      });
      setForm({ ...form, name: "", area_acres: "" });
      setShowForm(false);
      reload();
    } catch (err) {
      setFormError(errorMessage(err));
    } finally {
      setSaving(false);
    }
  };

  const deleteField = async (field) => {
    if (
      !window.confirm(`Delete field "${field.name}" and all its sensor data?`)
    )
      return;
    try {
      await api.delete(`/api/fields/${field.id}`);
      reload();
    } catch (err) {
      setError(errorMessage(err));
    }
  };

  const input =
    "w-full rounded border border-gray-300 px-3 py-2 focus:border-green-600 focus:outline-none";

  if (loading) return <p className="text-gray-500">Loading...</p>;

  if (!farm) {
    return (
      <div className="space-y-3">
        <div className="rounded bg-red-50 p-3 text-sm text-red-700">
          {error || "Farm not found"}
        </div>
        <Link to="/" className="text-green-700 underline">
          ← Back to dashboard
        </Link>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div>
        <Link to="/" className="text-sm text-green-700 hover:underline">
          ← All farms
        </Link>
        <div className="mt-1 flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold text-gray-800">{farm.name}</h1>
            <p className="text-sm text-gray-500">{farm.location}</p>
          </div>
          <button
            onClick={() => setShowForm(!showForm)}
            className="rounded bg-green-700 px-4 py-2 text-sm font-medium text-white hover:bg-green-800"
          >
            {showForm ? "Cancel" : "+ Add field"}
          </button>
        </div>
      </div>

      {error && (
        <div className="rounded bg-red-50 p-3 text-sm text-red-700">
          {error}
        </div>
      )}

      {showForm && (
        <form
          onSubmit={addField}
          className="space-y-3 rounded-xl bg-white p-5 shadow"
        >
          <h2 className="font-semibold text-gray-700">New field</h2>
          {formError && (
            <div className="rounded bg-red-50 p-3 text-sm text-red-700">
              {formError}
            </div>
          )}
          <div className="grid gap-3 sm:grid-cols-2">
            <div>
              <label className="mb-1 block text-sm font-medium">
                Field name
              </label>
              <input
                value={form.name}
                onChange={set("name")}
                className={input}
                placeholder="e.g. North Plot"
              />
            </div>
            <div>
              <label className="mb-1 block text-sm font-medium">
                Area (acres)
              </label>
              <input
                type="number"
                step="0.1"
                min="0.1"
                value={form.area_acres}
                onChange={set("area_acres")}
                className={input}
                placeholder="e.g. 2.5"
              />
            </div>
            <div>
              <label className="mb-1 block text-sm font-medium">Crop</label>
              <select
                value={form.crop_type}
                onChange={set("crop_type")}
                className={input}
              >
                {CROPS.map((c) => (
                  <option key={c} value={c}>
                    {cap(c)}
                  </option>
                ))}
              </select>
            </div>
            <div>
              <label className="mb-1 block text-sm font-medium">
                Soil type
              </label>
              <select
                value={form.soil_type}
                onChange={set("soil_type")}
                className={input}
              >
                {SOILS.map((s) => (
                  <option key={s} value={s}>
                    {cap(s)}
                  </option>
                ))}
              </select>
            </div>
            <div>
              <label className="mb-1 block text-sm font-medium">
                Planting date
              </label>
              <input
                type="date"
                max={todayLocal()}
                value={form.planting_date}
                onChange={set("planting_date")}
                className={input}
              />
            </div>
          </div>
          <button
            type="submit"
            disabled={saving}
            className="rounded bg-green-700 px-4 py-2 text-sm font-medium text-white hover:bg-green-800 disabled:opacity-60"
          >
            {saving ? "Saving..." : "Save field"}
          </button>
        </form>
      )}

      <div className="rounded-xl bg-white p-5 shadow">
        <h2 className="mb-3 font-semibold text-gray-700">
          Fields ({fields.length})
        </h2>

        {fields.length === 0 && (
          <p className="text-gray-500">No fields yet. Click "+ Add field".</p>
        )}

        <div className="grid gap-4 sm:grid-cols-2">
          {fields.map((f) => (
            <div key={f.id} className="rounded-lg border p-4">
              <div className="flex items-start justify-between">
                <div>
                  <p className="font-semibold text-gray-800">{f.name}</p>
                  <p className="text-xs text-gray-400">Field ID: {f.id}</p>
                </div>
                <span className="rounded-full bg-green-100 px-2 py-0.5 text-xs text-green-800">
                  {cap(f.crop_type)}
                </span>
              </div>
              <p className="mt-2 text-sm text-gray-600">
                {cap(f.soil_type)} soil · {f.area_acres} acres
              </p>
              <p className="text-sm text-gray-500">
                Planted: {f.planting_date}
              </p>
              <div className="mt-3 flex items-center justify-between">
                <Link
                  to={`/fields/${f.id}`}
                  className="rounded bg-green-700 px-3 py-1 text-sm text-white hover:bg-green-800"
                >
                  View live data
                </Link>
                <button
                  onClick={() => deleteField(f)}
                  className="rounded px-3 py-1 text-sm text-red-600 hover:bg-red-50"
                >
                  Delete
                </button>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
