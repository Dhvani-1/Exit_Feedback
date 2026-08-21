import React, { useState, useEffect, useCallback } from 'react';
import { Shield, Search, Calendar, Filter, AlertCircle, Loader2, ArrowUpDown, ChevronLeft, ChevronRight, User } from 'lucide-react';
import api from '../services/api';
import Pagination from '../components/common/Pagination';
import { formatIndianDateTime } from '../utils/dateUtils';

const AuditLogPage = () => {
  const [logs, setLogs] = useState([]);
  const [total, setTotal] = useState(0);
  const [totalPages, setTotalPages] = useState(1);
  const [page, setPage] = useState(1);
  const [pageSize] = useState(15);

  // Filter state
  const [search, setSearch] = useState('');
  const [eventType, setEventType] = useState('');
  const [startDate, setStartDate] = useState('');
  const [endDate, setEndDate] = useState('');

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const fetchAuditLogs = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const params = new URLSearchParams({
        page: page.toString(),
        page_size: pageSize.toString(),
      });

      if (search.trim()) params.append('search', search.trim());
      if (eventType.trim()) params.append('event_type', eventType.trim());
      if (startDate) params.append('date_start', startDate);
      if (endDate) params.append('date_end', endDate);

      const res = await api.get(`/dashboard/audit?${params.toString()}`);
      setLogs(res.data.items);
      setTotal(res.data.total);
      setTotalPages(res.data.total_pages);
    } catch (err) {
      setError(err.message || 'Failed to load system audit logs');
    } finally {
      setLoading(false);
    }
  }, [page, pageSize, search, eventType, startDate, endDate]);

  useEffect(() => {
    fetchAuditLogs();
  }, [fetchAuditLogs]);

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-extrabold text-white tracking-tight flex items-center gap-3">
            <Shield className="w-6 h-6 text-indigo-400" />
            System Audit Log Viewer
          </h1>
          <p className="text-xs text-slate-400 mt-1">
            Read-only immutable historical audit trail of employee lifecycle events, email dispatches, and feedback submissions
          </p>
        </div>
      </div>

      {/* Filter Bar */}
      <div className="p-4 bg-slate-900/80 border border-slate-800 rounded-2xl shadow-lg space-y-3 md:space-y-0 md:flex md:items-center md:gap-4">
        {/* Search */}
        <div className="relative flex-1">
          <Search className="w-4 h-4 text-slate-500 absolute left-3.5 top-1/2 -translate-y-1/2" />
          <input
            type="text"
            value={search}
            onChange={(e) => {
              setSearch(e.target.value);
              setPage(1);
            }}
            placeholder="Search by Employee Name, Event Type, or Actor..."
            className="w-full pl-10 pr-4 py-2 bg-slate-950/70 border border-slate-800 rounded-xl text-xs text-white placeholder-slate-500 focus:outline-none focus:border-indigo-500 transition"
          />
        </div>

        {/* Event Type Filter */}
        <div className="min-w-[160px]">
          <select
            value={eventType}
            onChange={(e) => {
              setEventType(e.target.value);
              setPage(1);
            }}
            className="w-full px-3 py-2 bg-slate-950/70 border border-slate-800 rounded-xl text-xs text-slate-200 focus:outline-none focus:border-indigo-500 transition cursor-pointer"
          >
            <option value="">All Event Types</option>
            <option value="FEEDBACK_RECORD_CREATED">FEEDBACK_RECORD_CREATED</option>
            <option value="INITIAL_EMAIL_SENT">INITIAL_EMAIL_SENT</option>
            <option value="REMINDER_SENT">REMINDER_SENT</option>
            <option value="FEEDBACK_SUBMITTED">FEEDBACK_SUBMITTED</option>
            <option value="REMINDER_CANCELLED">REMINDER_CANCELLED</option>
            <option value="FEEDBACK_EXPIRED">FEEDBACK_EXPIRED</option>
          </select>
        </div>

        {/* Start Date */}
        <div className="flex items-center gap-2">
          <span className="text-xs text-slate-400">From:</span>
          <input
            type="date"
            value={startDate}
            onChange={(e) => {
              setStartDate(e.target.value);
              setPage(1);
            }}
            className="px-3 py-2 bg-slate-950/70 border border-slate-800 rounded-xl text-xs text-slate-200 focus:outline-none focus:border-indigo-500"
          />
        </div>

        {/* End Date */}
        <div className="flex items-center gap-2">
          <span className="text-xs text-slate-400">To:</span>
          <input
            type="date"
            value={endDate}
            onChange={(e) => {
              setEndDate(e.target.value);
              setPage(1);
            }}
            className="px-3 py-2 bg-slate-950/70 border border-slate-800 rounded-xl text-xs text-slate-200 focus:outline-none focus:border-indigo-500"
          />
        </div>
      </div>

      {/* Error Alert */}
      {error && (
        <div className="p-4 bg-rose-500/10 border border-rose-500/30 rounded-2xl flex items-center justify-between text-rose-400 text-sm">
          <div className="flex items-center gap-3">
            <AlertCircle className="w-5 h-5 shrink-0" />
            <span>{error}</span>
          </div>
          <button
            onClick={fetchAuditLogs}
            className="px-3 py-1 bg-rose-500/20 hover:bg-rose-500/30 rounded-xl text-xs font-bold transition"
          >
            Retry
          </button>
        </div>
      )}

      {/* Audit Log Table */}
      <div className="bg-slate-900/80 border border-slate-800 rounded-2xl shadow-xl overflow-hidden">
        {loading ? (
          <div className="p-12 flex justify-center items-center">
            <Loader2 className="w-8 h-8 text-indigo-400 animate-spin" />
          </div>
        ) : logs.length === 0 ? (
          <div className="p-12 text-center text-slate-500 text-sm">
            No audit logs match your search or date filter criteria.
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs border-collapse">
              <thead>
                <tr className="bg-slate-950/60 text-slate-400 font-semibold uppercase tracking-wider border-b border-slate-800">
                  <th className="py-3.5 px-5 w-44">Timestamp (IST)</th>
                  <th className="py-3.5 px-5">Employee</th>
                  <th className="py-3.5 px-5">Event Type</th>
                  <th className="py-3.5 px-5">Actor / Source</th>
                  <th className="py-3.5 px-5">Sanitized Log Details</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/60 text-slate-300">
                {logs.map((log) => (
                  <tr key={log.id} className="hover:bg-slate-800/40 transition">
                    <td className="py-3.5 px-5 font-mono text-slate-400">
                      {formatIndianDateTime(log.created_at)}
                    </td>
                    <td className="py-3.5 px-5 font-semibold text-white">
                      <div>{log.employee_name}</div>
                      <div className="text-[10px] text-slate-500 font-mono">{log.personal_email}</div>
                    </td>
                    <td className="py-3.5 px-5 font-mono text-sky-400 font-bold">
                      {log.event_type}
                    </td>
                    <td className="py-3.5 px-5">
                      <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[10px] font-bold bg-slate-800 text-slate-300 border border-slate-700">
                        {log.actor_type || 'SYSTEM'}
                      </span>
                    </td>
                    <td className="py-3.5 px-5 text-slate-300 max-w-xs truncate font-mono text-[11px]">
                      {log.details || '—'}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        <Pagination
          page={page}
          totalPages={totalPages}
          totalItems={total}
          pageSize={pageSize}
          onPageChange={(newPage) => setPage(newPage)}
        />
      </div>
    </div>
  );
};

export default AuditLogPage;
