import React, { useState, useEffect } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import { ArrowLeft, Edit3, Ban, User, Mail, Calendar, Clock, Shield, AlertCircle, Send, RefreshCw, CheckCircle2, History } from 'lucide-react';
import api from '../services/api';
import StatusBadge from '../components/common/StatusBadge';
import EmailStatusBadge from '../components/common/EmailStatusBadge';
import EmailHistoryTable from '../components/employees/EmailHistoryTable';
import RescheduleModal from '../components/employees/RescheduleModal';
import Modal from '../components/common/Modal';
import { formatIndianDateTime, formatIndianDate } from '../utils/dateUtils';

const EmployeeDetailPage = () => {
  const { id } = useParams();
  const navigate = useNavigate();

  const [employee, setEmployee] = useState(null);
  const [emailJobs, setEmailJobs] = useState([]);
  const [auditLogs, setAuditLogs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [actionMessage, setActionMessage] = useState('');

  const [cancelModalOpen, setCancelModalOpen] = useState(false);
  const [rescheduleModalOpen, setRescheduleModalOpen] = useState(false);
  const [actionLoading, setActionLoading] = useState(false);

  const fetchEmployeeData = async () => {
    try {
      setLoading(true);
      setError('');
      const [empRes, historyRes, auditRes] = await Promise.all([
        api.get(`/employees/${id}`),
        api.get(`/employees/${id}/email-history`),
        api.get(`/employees/${id}/audit-logs`).catch(() => ({ data: [] })),
      ]);
      setEmployee(empRes.data);
      setEmailJobs(historyRes.data);
      setAuditLogs(auditRes.data);
    } catch (err) {
      setError(err.message || 'Failed to load employee details');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchEmployeeData();
  }, [id]);

  const activeJob = emailJobs.length > 0 ? emailJobs[0] : null;

  const handleSendNow = async () => {
    try {
      setActionLoading(true);
      setActionMessage('');
      await api.post(`/email/employees/${id}/send-now`);
      setActionMessage('Initial feedback email sent successfully!');
      fetchEmployeeData();
    } catch (err) {
      alert(err.message || 'Failed to send email now');
    } finally {
      setActionLoading(false);
    }
  };

  const handleCancelEmail = async () => {
    try {
      setActionLoading(true);
      setActionMessage('');
      await api.post(`/email/employees/${id}/cancel`);
      setActionMessage('Email job cancelled successfully.');
      fetchEmployeeData();
    } catch (err) {
      alert(err.message || 'Failed to cancel email job');
    } finally {
      setActionLoading(false);
    }
  };

  const handleReschedule = async (newScheduledAtUtc) => {
    try {
      setActionLoading(true);
      setActionMessage('');
      await api.post(`/email/employees/${id}/reschedule`, { scheduled_at: newScheduledAtUtc });
      setActionMessage('Email job rescheduled successfully.');
      fetchEmployeeData();
    } catch (err) {
      alert(err.message || 'Failed to reschedule email job');
    } finally {
      setActionLoading(false);
    }
  };

  const handleRetryFailed = async () => {
    try {
      setActionLoading(true);
      setActionMessage('');
      await api.post(`/email/employees/${id}/retry`);
      setActionMessage('Failed email job reset to SCHEDULED for retry.');
      fetchEmployeeData();
    } catch (err) {
      alert(err.message || 'Failed to retry email job');
    } finally {
      setActionLoading(false);
    }
  };

  const handleConfirmCancelEmployee = async () => {
    try {
      await api.post(`/employees/${id}/cancel`);
      fetchEmployeeData();
    } catch (err) {
      alert(err.message || 'Failed to cancel employee schedule');
    }
  };

  if (loading) {
    return (
      <div className="flex justify-center items-center min-h-[400px]">
        <div className="animate-spin rounded-full h-10 w-10 border-t-2 border-b-2 border-sky-500" />
      </div>
    );
  }

  if (error || !employee) {
    return (
      <div className="space-y-4">
        <Link
          to="/employees"
          className="inline-flex items-center gap-2 px-3 py-1.5 rounded-xl text-slate-400 hover:text-white bg-slate-900 border border-slate-800 text-xs font-semibold"
        >
          <ArrowLeft className="w-4 h-4" />
          Back to Directory
        </Link>
        <div className="p-6 bg-rose-500/10 border border-rose-500/30 rounded-2xl flex items-center gap-3 text-rose-400">
          <AlertCircle className="w-6 h-6 shrink-0" />
          <span>{error || 'Employee record not found'}</span>
        </div>
      </div>
    );
  }

  return (
    <div className="max-w-4xl mx-auto space-y-6">
      {/* Navigation Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div className="flex items-center gap-3">
          <Link
            to="/employees"
            className="p-2 rounded-xl text-slate-400 hover:text-white bg-slate-900 border border-slate-800 transition"
          >
            <ArrowLeft className="w-5 h-5" />
          </Link>
          <div>
            <div className="flex items-center gap-3">
              <h1 className="text-2xl font-extrabold text-white tracking-tight">{employee.full_name || employee.employee_name}</h1>
              <StatusBadge status={employee.status} />
            </div>
            <p className="text-xs text-slate-400 mt-0.5 font-mono">
              Personal Email: <span className="text-sky-400 font-semibold">{employee.personal_email}</span>
            </p>
          </div>
        </div>

        {/* Action Buttons */}
        <div className="flex items-center gap-2">
          <Link
            to={`/employees/${id}/edit`}
            className="inline-flex items-center gap-2 px-4 py-2 bg-slate-800 hover:bg-slate-700 text-slate-200 hover:text-white text-xs font-semibold rounded-xl border border-slate-700 transition"
          >
            <Edit3 className="w-4 h-4 text-amber-400" />
            Edit Record
          </Link>
          {employee.status === 'SCHEDULED' && (
            <button
              onClick={() => setCancelModalOpen(true)}
              className="inline-flex items-center gap-2 px-4 py-2 bg-rose-500/10 hover:bg-rose-500/20 text-rose-400 text-xs font-semibold rounded-xl border border-rose-500/30 transition"
            >
              <Ban className="w-4 h-4" />
              Cancel Schedule
            </button>
          )}
        </div>
      </div>

      {/* Action Notification Banner */}
      {actionMessage && (
        <div className="p-4 bg-emerald-500/10 border border-emerald-500/30 rounded-2xl flex items-center gap-3 text-emerald-400 text-sm animate-in fade-in">
          <CheckCircle2 className="w-5 h-5 shrink-0" />
          <span>{actionMessage}</span>
        </div>
      )}

      {/* Grid of Sections */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        {/* Main Details (2 cols) */}
        <div className="md:col-span-2 space-y-6">
          {/* Section 1: Employee Information */}
          <div className="bg-slate-900/80 border border-slate-800 rounded-3xl p-6 shadow-xl space-y-4">
            <h2 className="text-sm font-bold text-white uppercase tracking-wider text-slate-400 border-b border-slate-800 pb-3 flex items-center gap-2">
              <User className="w-4 h-4 text-sky-400" />
              Employee Information
            </h2>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div className="p-3.5 bg-slate-950/50 rounded-2xl border border-slate-800/80">
                <span className="text-[11px] font-semibold uppercase text-slate-500 block mb-1">Full Name</span>
                <span className="text-sm font-bold text-white">{employee.full_name || employee.employee_name}</span>
              </div>

              <div className="p-3.5 bg-slate-950/50 rounded-2xl border border-slate-800/80">
                <span className="text-[11px] font-semibold uppercase text-slate-500 block mb-1 flex items-center gap-1">
                  <Mail className="w-3 h-3 text-slate-400" />
                  Personal Email Address
                </span>
                <span className="text-sm font-mono font-semibold text-slate-200">{employee.personal_email}</span>
              </div>

              <div className="p-3.5 bg-slate-950/50 rounded-2xl border border-slate-800/80">
                <span className="text-[11px] font-semibold uppercase text-slate-500 block mb-1 flex items-center gap-1">
                  <Calendar className="w-3 h-3 text-slate-400" />
                  Last Working Date
                </span>
                <span className="text-sm font-semibold text-slate-200">{employee.last_working_date}</span>
              </div>

              <div className="p-3.5 bg-slate-950/50 rounded-2xl border border-slate-800/80">
                <span className="text-[11px] font-semibold uppercase text-slate-500 block mb-1 flex items-center gap-1">
                  <Clock className="w-3 h-3 text-amber-400" />
                  Feedback Due Date (3-Mo)
                </span>
                <span className="text-sm font-extrabold text-amber-300 font-mono">{employee.feedback_due_date}</span>
              </div>

              <div className="p-3.5 bg-slate-950/50 rounded-2xl border border-slate-800/80">
                <span className="text-[11px] font-semibold uppercase text-slate-500 block mb-1">Designation</span>
                <span className="text-sm font-semibold text-slate-200">{employee.designation || '—'}</span>
              </div>

              <div className="p-3.5 bg-slate-950/50 rounded-2xl border border-slate-800/80">
                <span className="text-[11px] font-semibold uppercase text-slate-500 block mb-1">Start Date / Date of Joining</span>
                <span className="text-sm font-semibold text-slate-200">{employee.start_date || '—'}</span>
              </div>

              <div className="p-3.5 bg-slate-950/50 rounded-2xl border border-slate-800/80">
                <span className="text-[11px] font-semibold uppercase text-slate-500 block mb-1">Tenure</span>
                <span className="text-sm font-semibold text-slate-200">{employee.tenure || '—'}</span>
              </div>
            </div>
          </div>

          {/* Section 2: Email Audit History Table */}
          <div className="bg-slate-900/80 border border-slate-800 rounded-3xl p-6 shadow-xl space-y-4">
            <h2 className="text-sm font-bold text-white uppercase tracking-wider text-slate-400 border-b border-slate-800 pb-3 flex items-center gap-2">
              <Mail className="w-4 h-4 text-sky-400" />
              Email Audit History
            </h2>
            <EmailHistoryTable jobs={emailJobs} />
          </div>

          {/* Section 3: Feedback Audit Log Timeline */}
          <div className="bg-slate-900/80 border border-slate-800 rounded-3xl p-6 shadow-xl space-y-4">
            <h2 className="text-sm font-extrabold text-white tracking-tight border-b border-slate-800 pb-3 flex items-center gap-2">
              <History className="w-4 h-4 text-sky-400" />
              Unified Chronological Audit & Event Timeline
            </h2>
            {auditLogs.length === 0 ? (
              <p className="text-xs text-slate-500 italic">No historical audit events recorded yet.</p>
            ) : (
              <div className="relative border-l border-slate-800 ml-2.5 pl-4 space-y-4">
                {auditLogs.map((log) => (
                  <div key={log.id} className="relative group">
                    <div className="absolute -left-[21px] top-1 w-2.5 h-2.5 rounded-full bg-sky-500 border-2 border-slate-900" />
                    <div className="p-3.5 bg-slate-950/60 border border-slate-800/80 rounded-2xl text-xs space-y-1 hover:border-slate-700 transition">
                      <div className="flex items-center justify-between gap-2">
                        <div className="flex items-center gap-2">
                          <span className="font-bold text-sky-300 font-mono">{log.event_type}</span>
                          <span className="px-2 py-0.5 rounded-full text-[9px] font-extrabold bg-slate-800 text-slate-300 border border-slate-700">
                            {log.actor_type || 'SYSTEM'}
                          </span>
                        </div>
                        <span className="text-[10px] text-slate-500 font-mono">
                          {formatIndianDateTime(log.created_at)}
                        </span>
                      </div>
                      {log.details && (
                        <p className="text-slate-400 font-mono text-[11px] pt-1 border-t border-slate-900">
                          {log.details}
                        </p>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>

        {/* Sidebar Status & Control Cards (1 col) */}
        <div className="space-y-6">
          {/* Feedback Status Card */}
          <div className="bg-slate-900/80 border border-slate-800 rounded-3xl p-6 shadow-xl space-y-4">
            <h3 className="text-xs font-bold text-slate-400 uppercase tracking-wider border-b border-slate-800 pb-2">
              Feedback Status
            </h3>
            <div className="flex items-center justify-between">
              <span className="text-xs text-slate-400">Current Status:</span>
              <span className={`inline-flex items-center px-3 py-1 rounded-full text-xs font-bold border ${
                employee.feedback_status === 'SUBMITTED'
                  ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20'
                  : employee.feedback_status === 'EXPIRED'
                  ? 'bg-slate-500/10 text-slate-400 border-slate-500/20'
                  : 'bg-amber-500/10 text-amber-400 border-amber-500/20'
              }`}>
                {employee.feedback_status || 'PENDING'}
              </span>
            </div>
            {employee.feedback_submitted_at && (
              <div className="text-xs text-slate-400">
                Submitted on: <span className="text-white font-mono">{formatIndianDateTime(employee.feedback_submitted_at)}</span>
              </div>
            )}
          </div>

          {/* Email Controls Card */}
          <div className="bg-slate-900/80 border border-slate-800 rounded-3xl p-6 shadow-xl space-y-4">
            <h3 className="text-xs font-bold text-slate-400 uppercase tracking-wider border-b border-slate-800 pb-2">
              Active Email Job Controls
            </h3>

            {activeJob ? (
              <div className="space-y-3">
                <div className="flex items-center justify-between text-xs">
                  <span className="text-slate-400">Status:</span>
                  <EmailStatusBadge status={activeJob.status} />
                </div>
                <div className="flex items-center justify-between text-xs">
                  <span className="text-slate-400">Scheduled At (IST):</span>
                  <span className="font-mono text-slate-200">{formatIndianDateTime(activeJob.scheduled_at)}</span>
                </div>

                <div className="pt-2 space-y-2">
                  {activeJob.status === 'SCHEDULED' && (
                    <>
                      <button
                        onClick={handleSendNow}
                        disabled={actionLoading}
                        className="w-full inline-flex items-center justify-center gap-2 px-3.5 py-2 bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-bold rounded-xl shadow-lg transition disabled:opacity-50"
                      >
                        <Send className="w-3.5 h-3.5" />
                        Send Now (Force Dispatch)
                      </button>
                      <button
                        onClick={() => setRescheduleModalOpen(true)}
                        disabled={actionLoading}
                        className="w-full inline-flex items-center justify-center gap-2 px-3.5 py-2 bg-slate-800 hover:bg-slate-700 text-sky-400 text-xs font-semibold rounded-xl border border-slate-700 transition"
                      >
                        <Clock className="w-3.5 h-3.5" />
                        Reschedule
                      </button>
                      <button
                        onClick={handleCancelEmail}
                        disabled={actionLoading}
                        className="w-full inline-flex items-center justify-center gap-2 px-3.5 py-2 bg-rose-500/10 hover:bg-rose-500/20 text-rose-400 text-xs font-semibold rounded-xl border border-rose-500/30 transition"
                      >
                        <Ban className="w-3.5 h-3.5" />
                        Cancel Email Job
                      </button>
                    </>
                  )}

                  {activeJob.status === 'FAILED' && (
                    <button
                      onClick={handleRetryFailed}
                      disabled={actionLoading}
                      className="w-full inline-flex items-center justify-center gap-2 px-3.5 py-2 bg-amber-600 hover:bg-amber-500 text-white text-xs font-bold rounded-xl shadow-lg transition"
                    >
                      <RefreshCw className="w-3.5 h-3.5" />
                      Retry Failed Job
                    </button>
                  )}
                </div>
              </div>
            ) : (
              <p className="text-xs text-slate-500">No active email job associated with this record.</p>
            )}
          </div>
        </div>
      </div>

      {/* Cancellation Confirmation Modal */}
      <Modal
        isOpen={cancelModalOpen}
        onClose={() => setCancelModalOpen(false)}
        onConfirm={handleConfirmCancelEmployee}
        title="Cancel Employee Schedule"
        message={`Are you sure you want to cancel the feedback schedule for ${employee.full_name || employee.employee_name}? Unsent email jobs will be cancelled immediately.`}
        confirmText="Cancel Schedule"
        isDangerous={true}
      />

      {/* Reschedule Modal */}
      {activeJob && (
        <RescheduleModal
          isOpen={rescheduleModalOpen}
          onClose={() => setRescheduleModalOpen(false)}
          onConfirm={handleReschedule}
          currentScheduledAt={activeJob.scheduled_at}
        />
      )}
    </div>
  );
};

export default EmployeeDetailPage;
