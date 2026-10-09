import { useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import api, { errorMessage } from "../api/client";
import AuthShell from "../components/AuthShell";
import Button from "../components/ui/Button";
import FormField from "../components/ui/FormField";
import { Banner } from "../components/ui/Feedback";

export default function ResetPassword() {
  const [searchParams] = useSearchParams();
  const token = searchParams.get("token") || "";
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [errors, setErrors] = useState({});
  const [error, setError] = useState("");
  const [complete, setComplete] = useState(false);
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (event) => {
    event.preventDefault();
    if (loading) return;
    setError("");
    const nextErrors = {};
    if (password.length < 8) nextErrors.password = "Password must be at least 8 characters";
    else if (!/[A-Za-z]/.test(password) || !/\d/.test(password)) {
      nextErrors.password = "Password must include at least one letter and one number";
    }
    if (password !== confirmPassword) nextErrors.confirmPassword = "Passwords do not match";
    setErrors(nextErrors);
    if (Object.keys(nextErrors).length || !token) return;

    setLoading(true);
    try {
      await api.post("/api/auth/password-reset/confirm", { token, password });
      setComplete(true);
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setLoading(false);
    }
  };

  return (
    <AuthShell
      title={complete ? "Password updated" : "Set a new password"}
      subtitle={complete ? "Your password has been changed." : "Choose a new password for your account."}
      footer={<Link to="/login" className="font-medium text-forest-700 hover:underline">Back to login</Link>}
    >
      {complete ? (
        <Banner tone="success" title="Password reset complete">
          You can now sign in with your new password.
        </Banner>
      ) : !token ? (
        <Banner tone="error" title="Reset link is missing">
          Request a new link from the <Link to="/forgot-password" className="font-medium underline">forgot password page</Link>.
        </Banner>
      ) : (
        <form onSubmit={handleSubmit} className="space-y-4">
          {error && <Banner tone="error" title="Could not reset password">{error}</Banner>}
          <FormField
            label="New password"
            type="password"
            autoComplete="new-password"
            value={password}
            onChange={(event) => setPassword(event.target.value)}
            error={errors.password}
            hint="At least 8 characters, with a letter and a number"
          />
          <FormField
            label="Confirm new password"
            type="password"
            autoComplete="new-password"
            value={confirmPassword}
            onChange={(event) => setConfirmPassword(event.target.value)}
            error={errors.confirmPassword}
          />
          <Button type="submit" loading={loading} className="w-full">
            {loading ? "Updating password..." : "Update password"}
          </Button>
        </form>
      )}
    </AuthShell>
  );
}