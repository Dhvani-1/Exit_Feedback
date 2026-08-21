import React from 'react';
import { Mail, Clock, CheckCircle2, AlertTriangle } from 'lucide-react';
import EmailStatusBadge from '../common/EmailStatusBadge';
import { formatIndianDateTime } from '../../utils/dateUtils';

const EmailHistoryTable = ({ jobs }) => {
  if (!jobs || jobs.length === 0) {
    return (
      <div className="p-6 text-center text-slate-500 text-xs bg-slate-950/40 rounded-2xl border border-slate-800/60">
        No email history recorded for this employee yet.
      </div>
    );
  }

  return (
    <div className="overflow-x-auto rounded-2xl border border-slate-800/80 bg-slate-950/60">
      <table className="w-full text-left text-xs border-collapse">
        <thead>
          <tr className="bg-slate-900/80 text-slate-400 font-semibold uppercase tracking-wider border-b border-slate-800">
            <th className="py-3 px-4">Email Type</th>
            <th className="py-3 px-4">Recipient</th>
            <th className="py-3 px-4">Scheduled At (IST)</th>
            <th className="py-3 px-4">Status</th>
            <th className="py-3 px-4">Attempts</th>
            <th className="py-3 px-4">Delivery Details / Error</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-slate-800/60 text-slate-300">
          {jobs.map((job) => (
            <tr key={job.id} className="hover:bg-slate-900/40 transition">
              <td className="py-3.5 px-4 font-mono font-semibold text-sky-400 flex items-center gap-2">
                <Mail className="w-3.5 h-3.5 text-sky-400" />
                {job.email_type}
              </td>
              <td className="py-3.5 px-4 font-mono text-[11px] text-slate-200">{job.recipient_email}</td>
              <td className="py-3.5 px-4 text-slate-300 font-medium font-mono">
                {formatIndianDateTime(job.scheduled_at)}
              </td>
              <td className="py-3.5 px-4">
                <EmailStatusBadge status={job.status} />
              </td>
              <td className="py-3.5 px-4 font-semibold text-slate-300">
                {job.attempt_count} / {job.max_attempts}
              </td>
              <td className="py-3.5 px-4 text-[11px]">
                {job.status === 'SENT' && (
                  <div className="flex items-center gap-1.5 text-emerald-400 font-mono">
                    <CheckCircle2 className="w-3.5 h-3.5" />
                    <span>Sent: {formatIndianDateTime(job.sent_at)}</span>
                  </div>
                )}
                {job.status === 'FAILED' && (
                  <div className="flex items-start gap-1.5 text-rose-400">
                    <AlertTriangle className="w-3.5 h-3.5 shrink-0 mt-0.5" />
                    <span className="truncate max-w-xs">{job.last_error || 'Delivery failed'}</span>
                  </div>
                )}
                {job.status === 'SCHEDULED' && (
                  <div className="flex items-center gap-1.5 text-sky-400/80">
                    <Clock className="w-3.5 h-3.5" />
                    <span>Awaiting worker execution</span>
                  </div>
                )}
                {job.status === 'CANCELLED' && (
                  <span className="text-slate-500 italic">Cancelled on {formatIndianDateTime(job.cancelled_at || job.updated_at)}</span>
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
};

export default EmailHistoryTable;
