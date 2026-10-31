import { useState } from "react";
import { Link } from "react-router-dom";
import api, { errorMessage } from "../api/client";
import AuthShell from "../components/AuthShell";
import Button from "../components/ui/Button";
import FormField from "../components/ui/FormField";
import { Banner } from "../components/ui/Feedback";

export default function ForgotPassword() {
  const [email, setEmail] = useState("");
  const [message, setMessage] = useState("");
  const [resetUrl, setResetUrl] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (event) => {
    event.preventDefault();
    if (loading) return;
    setError("");
    setMessage("");
    setResetUrl("");
    setLoading(true);
    try {
      const { data } = await api.post("/api/auth/password-reset/request", { email: email.trim() });
      setMessage(data.message);
      setResetUrl(data.reset_url || "");
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setLoading(false);
    }
  };

  return (
    <AuthShell
      title="Forgot password?"
      subtitle="Enter the email address for your account and we’ll send a reset link."
      footer={<>Remembered it? <Link to="/login" className="font-medium text-forest-700 hover:underline">Back to login</Link></>}
    >
      <form onSubmit={handleSubmit} className="space-y-4">
        {error && <Banner tone="error" title="Could not request a reset">{error}</Banner>}
        {message && <Banner tone="success" title="Reset request received">{message}</Banner>}
        {resetUrl && (
          <Banner tone="info" title="Local development reset link">
            <a href={resetUrl} className="font-medium underline">Open password reset</a>
          </Banner>
        )}
        <FormField
          label="Email"
          type="email"
          autoComplete="email"
          value={email}
          onChange={(event) => setEmail(event.target.value)}
          placeholder="you@example.com"
        />
        <Button type="submit" loading={loading} className="w-full">
          {loading ? "Sending link..." : "Send reset link"}
        </Button>
      </form>
    </AuthShell>
  );
}