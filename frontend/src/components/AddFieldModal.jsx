import { useState } from "react";
import api, { errorMessage } from "../api/client";
import { CROPS, SOILS, cap, todayLocal } from "../constants";
import Button from "./ui/Button";
import FormField from "./ui/FormField";
import Modal from "./ui/Modal";
import { Banner } from "./ui/Feedback";

const initial = () => ({
  name: "",
  area_acres: "",
  crop_type: "wheat",
  soil_type: "loamy",
  planting_date: todayLocal(),
});

export default function AddFieldModal({ open, farmId, onClose, onCreated }) {
  const [form, setForm] = useState(initial);
  const [errors, setErrors] = useState({});
  const [error, setError] = useState("");
  const [saving, setSaving] = useState(false);

  const set = (key) => (e) => setForm({ ...form, [key]: e.target.value });

  const close = () => {
    setForm(initial());
    setErrors({});
    setError("");
    onClose();
  };

  const submit = async (e) => {
    e.preventDefault();
    if (saving) return;
    setError("");
    const found = {};
    const area = Number(form.area_acres);
    if (!form.name.trim()) found.name = "Enter a field name";
    if (!form.area_acres || !(area > 0)) found.area_acres = "Area must be greater than 0";
    if (!form.planting_date) found.planting_date = "Choose a planting date";
    else if (form.planting_date > todayLocal()) found.planting_date = "Planting date cannot be in the future";
    setErrors(found);
    if (Object.keys(found).length) return;

    setSaving(true);
    try {
      const { data } = await api.post(`/api/farms/${farmId}/fields`, {
        name: form.name.trim(),
        crop_type: form.crop_type,
        soil_type: form.soil_type,
        area_acres: area,
        planting_date: form.planting_date,
      });
      setForm(initial());
      await onCreated(data);
    } catch (err) {
      // e.g. duplicate field name
      setError(errorMessage(err));
    } finally {
      setSaving(false);
    }
  };


  return (
    <Modal open={open} title="Add a field" onClose={close} busy={saving}>
      <form onSubmit={submit} noValidate className="space-y-4">
        {error && <Banner tone="error">{error}</Banner>}
        <div className="grid gap-4 sm:grid-cols-2">
          <FormField label="Field name" value={form.name} onChange={set("name")} error={errors.name} placeholder="e.g. North Plot" />
          <FormField
            label="Area (acres)"
            type="number"
            step="0.1"
            min="0"
            value={form.area_acres}
            onChange={set("area_acres")}
            error={errors.area_acres}
            placeholder="e.g. 2.5"
          />
          <FormField label="Crop">
            {(props, cls) => (
              <select {...props} className={cls} value={form.crop_type} onChange={set("crop_type")}>
                {CROPS.map((c) => <option key={c} value={c}>{cap(c)}</option>)}
              </select>
            )}
          </FormField>
          <FormField label="Soil type">
            {(props, cls) => (
              <select {...props} className={cls} value={form.soil_type} onChange={set("soil_type")}>
                {SOILS.map((s) => <option key={s} value={s}>{cap(s)}</option>)}
              </select>
            )}
          </FormField>
        </div>
        <FormField
          label="Planting date"
          type="date"
          max={todayLocal()}
          value={form.planting_date}
          onChange={set("planting_date")}
          error={errors.planting_date}
        />
        <div className="flex justify-end gap-2 pt-2">
          <Button variant="secondary" onClick={close} disabled={saving}>Cancel</Button>
          <Button type="submit" loading={saving}>Save field</Button>
        </div>
      </form>
    </Modal>
  );
}
