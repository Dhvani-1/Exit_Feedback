import React, { useState, useEffect, useMemo } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import { ArrowLeft, Save, Calendar, Info, AlertCircle, Loader2, RefreshCw } from 'lucide-react';
import api from '../services/api';

const EmployeeEditPage = () => {
  const { id } = useParams();
  const navigate = useNavigate();

  const [formData, setFormData] = useState({
    full_name: '',
    personal_email: '',
    last_working_date: '',
    version: 1,
  });

  const [initialLwd, setInitialLwd] = useState('');
  const [initialDueDate, setInitialDueDate] = useState('');
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');
  const [isStale, setIsStale] = useState(false);

  const fetchEmployee = async () => {
    try {
      setLoading(true);
      setError('');
      setIsStale(false);
      const res = await api.get(`/employees/${id}`);
      const emp = res.data;
      setFormData({
        full_name: emp.full_name || emp.employee_name || '',
        personal_email: emp.personal_email,
        last_working_date: emp.last_working_date,
        designation: emp.designation || '',
        start_date: emp.start_date || '',
        tenure: emp.tenure || '',
        version: emp.version,
      });
      setInitialLwd(emp.last_working_date);
      setInitialDueDate(emp.feedback_due_date);
    } catch (err) {
      setError(err.message || 'Failed to load employee details');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchEmployee();
  }, [id]);

  const handleChange = (e) => {
    setFormData({
      ...formData,
      [e.target.name]: e.target.value,
    });
  };

  const previewDueDate = useMemo(() => {
    if (!formData.last_working_date) return '';
    if (formData.last_working_date === initialLwd) return initialDueDate;

    try {
      const parts = formData.last_working_date.split('-');
      if (parts.length !== 3) return '';
      const year = parseInt(parts[0], 10);
      const month = parseInt(parts[1], 10);
      const day = parseInt(parts[2], 10);

      if (isNaN(year) || isNaN(month) || isNaN(day)) return '';

      const targetMonthRaw = month + 3;
      const targetYear = year + Math.floor((targetMonthRaw - 1) / 12);
      const targetMonth = ((targetMonthRaw - 1) % 12) + 1;

      const maxDaysInTargetMonth = new Date(targetYear, targetMonth, 0).getDate();
      const targetDay = Math.min(day, maxDaysInTargetMonth);

      const formattedMonth = String(targetMonth).padStart(2, '0');
      const formattedDay = String(targetDay).padStart(2, '0');

      return `${targetYear}-${formattedMonth}-${formattedDay}`;
    } catch {
      return '';
    }
  }, [formData.last_working_date, initialLwd, initialDueDate]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setIsStale(false);
    setSaving(true);

    try {
      await api.put(`/employees/${id}`, {
        full_name: formData.full_name,
        personal_email: formData.personal_email,
        last_working_date: formData.last_working_date,
        designation: formData.designation,
        start_date: formData.start_date || null,
        tenure: formData.tenure,
        version: formData.version,
      });
      navigate(`/employees/${id}`);
    } catch (err) {
      if (err.code === 'STALE_EMPLOYEE_RECORD') {
        setIsStale(true);
      }
      setError(err.message || 'Failed to update employee record');
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return (
      <div className="flex justify-center items-center min-h-[400px]">
        <div className="animate-spin rounded-full h-10 w-10 border-t-2 border-b-2 border-sky-500" />
      </div>
    );
  }

  return (
    <div className="max-w-2xl mx-auto space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <Link
            to={`/employees/${id}`}
            className="p-2 rounded-xl text-slate-400 hover:text-white bg-slate-900 border border-slate-800 transition"
          >
            <ArrowLeft className="w-5 h-5" />
          </Link>
          <div>
            <h1 className="text-2xl font-extrabold text-white tracking-tight">Edit Employee</h1>
            <p className="text-xs text-slate-400 mt-0.5">
              Updating record for <span className="font-semibold text-sky-400">{formData.full_name}</span>
            </p>
          </div>
        </div>
      </div>

      {/* Error / Stale Conflict Alert */}
      {error && (
        <div className="p-4 bg-rose-500/10 border border-rose-500/30 rounded-2xl flex items-center justify-between gap-3 text-rose-400 text-sm">
          <div className="flex items-center gap-3">
            <AlertCircle className="w-5 h-5 shrink-0" />
            <span>{error}</span>
          </div>
          {isStale && (
            <button
              type="button"
              onClick={fetchEmployee}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-rose-500/20 hover:bg-rose-500/30 text-rose-300 rounded-xl text-xs font-semibold transition"
            >
              <RefreshCw className="w-3.5 h-3.5" />
              Reload Latest
            </button>
          )}
        </div>
      )}

      {/* Form Container */}
      <form onSubmit={handleSubmit} className="bg-slate-900/80 border border-slate-800 rounded-3xl p-6 md:p-8 shadow-2xl space-y-6">
        <div className="space-y-5">
          {/* Full Name */}
          <div>
            <label className="block text-xs font-semibold text-slate-300 uppercase tracking-wider mb-2">
              Full Name <span className="text-rose-400">*</span>
            </label>
            <input
              type="text"
              name="full_name"
              required
              value={formData.full_name}
              onChange={handleChange}
              className="w-full px-4 py-2.5 bg-slate-950/70 border border-slate-800 rounded-xl text-sm text-white focus:outline-none focus:border-sky-500"
            />
          </div>

          {/* Personal Email */}
          <div>
            <label className="block text-xs font-semibold text-slate-300 uppercase tracking-wider mb-2">
              Personal Email <span className="text-rose-400">*</span>
            </label>
            <input
              type="email"
              name="personal_email"
              required
              value={formData.personal_email}
              onChange={handleChange}
              className="w-full px-4 py-2.5 bg-slate-950/70 border border-slate-800 rounded-xl text-sm text-white focus:outline-none focus:border-sky-500 font-mono"
            />
          </div>

          {/* Last Working Date Input */}
          <div>
            <label className="block text-xs font-semibold text-slate-300 uppercase tracking-wider mb-2">
              Last Working Date <span className="text-rose-400">*</span>
            </label>
            <input
              type="date"
              name="last_working_date"
              required
              value={formData.last_working_date}
              onChange={handleChange}
              className="w-full px-4 py-2.5 bg-slate-950/70 border border-slate-800 rounded-xl text-sm text-white focus:outline-none focus:border-sky-500 cursor-pointer"
            />
          </div>

          {/* Designation Input */}
          <div>
            <label className="block text-xs font-semibold text-slate-300 uppercase tracking-wider mb-2">
              Designation
            </label>
            <input
              type="text"
              name="designation"
              value={formData.designation}
              onChange={handleChange}
              placeholder="e.g. Senior Manager / Executive"
              className="w-full px-4 py-2.5 bg-slate-950/70 border border-slate-800 rounded-xl text-sm text-white placeholder-slate-500 focus:outline-none focus:border-sky-500"
            />
          </div>

          {/* Start Date & Tenure Inputs (Grid) */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label className="block text-xs font-semibold text-slate-300 uppercase tracking-wider mb-2">
                Start Date / Date of Joining
              </label>
              <input
                type="date"
                name="start_date"
                value={formData.start_date}
                onChange={handleChange}
                className="w-full px-4 py-2.5 bg-slate-950/70 border border-slate-800 rounded-xl text-sm text-white focus:outline-none focus:border-sky-500 cursor-pointer"
              />
            </div>
            <div>
              <label className="block text-xs font-semibold text-slate-300 uppercase tracking-wider mb-2">
                Tenure
              </label>
              <input
                type="text"
                name="tenure"
                value={formData.tenure}
                onChange={handleChange}
                placeholder="e.g. 2 years 6 months"
                className="w-full px-4 py-2.5 bg-slate-950/70 border border-slate-800 rounded-xl text-sm text-white placeholder-slate-500 focus:outline-none focus:border-sky-500"
              />
            </div>
          </div>
        </div>

        {/* Recalculation Notice Box */}
        <div className="p-4 bg-sky-950/30 border border-sky-800/40 rounded-2xl flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div className="flex items-start gap-3">
            <div className="p-2 bg-sky-500/10 text-sky-400 rounded-xl mt-0.5 border border-sky-500/20">
              <Calendar className="w-5 h-5" />
            </div>
            <div>
              <div className="text-xs font-semibold text-slate-300">Feedback Due Date Calculation</div>
              <div className="text-xs text-slate-400 mt-0.5">
                {formData.last_working_date !== initialLwd ? (
                  <span className="text-amber-300 font-medium">
                    Last working date modified. Backend will automatically recalculate due date upon save.
                  </span>
                ) : (
                  <span>Recalculates automatically if Last Working Date changes.</span>
                )}
              </div>
            </div>
          </div>
          <div className="text-right shrink-0">
            <div className="text-lg font-extrabold text-amber-300 font-mono">
              {previewDueDate || '—'}
            </div>
            <div className="text-[10px] text-slate-500 flex items-center gap-1 justify-end mt-0.5">
              <Info className="w-3 h-3" />
              Recalculated on save
            </div>
          </div>
        </div>

        {/* Action Buttons */}
        <div className="flex items-center justify-end gap-3 pt-2 border-t border-slate-800">
          <Link
            to={`/employees/${id}`}
            className="px-5 py-2.5 text-xs font-semibold text-slate-300 hover:text-white bg-slate-800 hover:bg-slate-700 rounded-xl transition"
          >
            Cancel
          </Link>
          <button
            type="submit"
            disabled={saving}
            className="inline-flex items-center gap-2 px-5 py-2.5 bg-gradient-to-r from-sky-600 to-cyan-600 hover:from-sky-500 hover:to-cyan-500 text-white text-xs font-bold rounded-xl shadow-lg shadow-sky-900/30 transition disabled:opacity-50"
          >
            {saving ? (
              <>
                <Loader2 className="w-4 h-4 animate-spin" />
                Updating...
              </>
            ) : (
              <>
                <Save className="w-4 h-4" />
                Save Changes
              </>
            )}
          </button>
        </div>
      </form>
    </div>
  );
};

export default EmployeeEditPage;
