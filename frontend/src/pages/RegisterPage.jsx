import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import authService from "../services/authService";

export default function RegisterPage() {
  const navigate = useNavigate();
  const [form, setForm] = useState({ username: "", email: "", password: "" });
  const [errors, setErrors] = useState({});
  const [loading, setLoading] = useState(false);

  const set = (field) => (e) => setForm({ ...form, [field]: e.target.value });

  const handleSubmit = async (e) => {
    e.preventDefault();
    setErrors({});
    setLoading(true);
    try {
      await authService.register(form);
      navigate("/login");
    } catch (err) {
      setErrors(err.response?.data || { non_field_errors: "Registration failed." });
    } finally {
      setLoading(false);
    }
  };

  const fieldError = (key) =>
    errors[key] ? (
      <p className="text-xs text-red-600 mt-1">{errors[key]}</p>
    ) : null;

  return (
    <div className="bg-white rounded-xl shadow-sm p-8">
      <h2 className="text-xl font-semibold text-gray-800 mb-6">Create account</h2>

      {errors.non_field_errors && (
        <p className="text-sm text-red-600 bg-red-50 rounded-md px-3 py-2 mb-4">
          {errors.non_field_errors}
        </p>
      )}

      <form onSubmit={handleSubmit} className="space-y-4">
        {[
          { label: "Username", field: "username", type: "text" },
          { label: "Email", field: "email", type: "email" },
          { label: "Password", field: "password", type: "password" },
        ].map(({ label, field, type }) => (
          <div key={field}>
            <label className="block text-sm font-medium text-gray-700 mb-1">{label}</label>
            <input
              type={type}
              required
              value={form[field]}
              onChange={set(field)}
              className="w-full border border-gray-300 rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
            {fieldError(field)}
          </div>
        ))}

        <button
          type="submit"
          disabled={loading}
          className="w-full bg-blue-600 hover:bg-blue-700 disabled:opacity-50 text-white text-sm font-medium py-2 rounded-md transition-colors"
        >
          {loading ? "Creating account…" : "Register"}
        </button>
      </form>

      <p className="text-sm text-gray-500 text-center mt-6">
        Already have an account?{" "}
        <Link to="/login" className="text-blue-600 hover:underline">
          Sign in
        </Link>
      </p>
    </div>
  );
}
