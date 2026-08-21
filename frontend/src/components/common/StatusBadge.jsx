import React from 'react';

const StatusBadge = ({ status }) => {
  const isScheduled = status === 'SCHEDULED';
  
  return (
    <span
      className={`inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold tracking-wide border ${
        isScheduled
          ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/30'
          : 'bg-rose-500/10 text-rose-400 border-rose-500/30'
      }`}
    >
      <span
        className={`w-1.5 h-1.5 rounded-full ${
          isScheduled ? 'bg-emerald-400 animate-pulse' : 'bg-rose-400'
        }`}
      />
      {status}
    </span>
  );
};

export default StatusBadge;
