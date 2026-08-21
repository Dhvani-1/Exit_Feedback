/**
 * Date & Time Utility Functions for Indian Standard Time (IST, Asia/Kolkata)
 */

export const parseAsUtcDate = (dateInput) => {
  if (!dateInput) return null;
  if (dateInput instanceof Date) return dateInput;
  let str = String(dateInput).trim();
  
  // If ISO string lacks timezone offset info (e.g. '2026-08-21T06:20:00'), append 'Z' to denote UTC
  if (str.includes('T') && !str.endsWith('Z') && !str.includes('+') && !str.slice(10).includes('-')) {
    str = str + 'Z';
  } else if (!str.includes('T') && str.includes(' ') && !str.endsWith('Z')) {
    str = str.replace(' ', 'T') + 'Z';
  }
  
  const d = new Date(str);
  return isNaN(d.getTime()) ? null : d;
};

export const formatIndianDateTime = (dateInput) => {
  if (!dateInput) return '—';
  try {
    const d = parseAsUtcDate(dateInput);
    if (!d) return String(dateInput);
    return d.toLocaleString('en-IN', {
      timeZone: 'Asia/Kolkata',
      day: '2-digit',
      month: '2-digit',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
      hour12: true,
    });
  } catch (e) {
    return String(dateInput);
  }
};

export const formatIndianDate = (dateInput) => {
  if (!dateInput) return '—';
  try {
    const d = parseAsUtcDate(dateInput);
    if (!d) return String(dateInput);
    return d.toLocaleDateString('en-IN', {
      timeZone: 'Asia/Kolkata',
      day: '2-digit',
      month: '2-digit',
      year: 'numeric',
    });
  } catch (e) {
    return String(dateInput);
  }
};
