import { useState } from "react";
import api, { errorMessage } from "../api/client";
import Button from "./ui/Button";
import FormField from "./ui/FormField";
import Modal from "./ui/Modal";
import { Banner } from "./ui/Feedback";

const EMPTY = { name: "", location: "" };

export default function AddFarmModal({ open, onClose, onCreated }) {
  const [form, setForm] = useState(EMPTY);
  const [errors, setErrors] = useState({});
  const [error, setError] = useState("");
  const [saving, setSaving] = useState(false);

  const close = () => {
    setForm(EMPTY);
    setErrors({});
    setError("");
    onClose();
  };

  const submit = async (e) => {
    e.preventDefault();
    if (saving) return;
    setError("");
    const found = {};
    if (form.name.trim().length < 2) found.name = "Farm name must be at least 2 characters";
    if (form.location.trim().length < 2) found.location = "Please enter a location";
    setErrors(found);
    if (Object.keys(found).length) return;

    setSaving(true);
    try {
      const { data } = await api.post("/api/farms", {
        name: form.name.trim(),
        location: form.location.trim(),
      });
      setForm(EMPTY);
      await onCreated(data);
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setSaving(false);
    }
  };

  return (
    <Modal open={open} title="Add a farm" onClose={close} busy={saving}>
      <form onSubmit={submit} noValidate className="space-y-4">
        {error && <Banner tone="error">{error}</Banner>}
        <FormField
          label="Farm name"
          value={form.name}
          onChange={(e) => setForm({ ...form, name: e.target.value })}
          error={errors.name}
          placeholder="e.g. Mali Farm"
        />
        <FormField
          label="Location"
          value={form.location}
          onChange={(e) => setForm({ ...form, location: e.target.value })}
          error={errors.location}
          placeholder="e.g. Pune, Maharashtra"
        />
        <div className="flex justify-end gap-2 pt-2">
          <Button variant="secondary" onClick={close} disabled={saving}>Cancel</Button>
          <Button type="submit" loading={saving}>Save farm</Button>
        </div>
      </form>
    </Modal>
  );
}
