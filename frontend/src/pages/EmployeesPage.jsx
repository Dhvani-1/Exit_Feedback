import React, { useState, useEffect, useCallback } from 'react';
import { Link } from 'react-router-dom';
import { Search, UserPlus, Eye, Edit3, Ban, ArrowUpDown, AlertCircle, FileSpreadsheet, Download } from 'lucide-react';
import api from '../services/api';
import StatusBadge from '../components/common/StatusBadge';
import EmailStatusBadge from '../components/common/EmailStatusBadge';
import Pagination from '../components/common/Pagination';
import Modal from '../components/common/Modal';
import ExcelImportModal from '../components/employees/ExcelImportModal';

const EmployeesPage = () => {
  const [employees, setEmployees] = useState([]);
  const [emailJobsMap, setEmailJobsMap] = useState({});
  const [total, setTotal] = useState(0);
  const [totalPages, setTotalPages] = useState(1);
  const [page, setPage] = useState(1);
  const [pageSize] = useState(10);

  // Search & Filters state
  const [search, setSearch] = useState('');
  const [statusFilter, setStatusFilter] = useState('');
  const [feedbackStatusFilter, setFeedbackStatusFilter] = useState('');
  const [sortBy, setSortBy] = useState('created_at');
  const [sortOrder, setSortOrder] = useState('desc');

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // Modals state
  const [cancelModalOpen, setCancelModalOpen] = useState(false);
  const [selectedEmployee, setSelectedEmployee] = useState(null);
  const [excelModalOpen, setExcelModalOpen] = useState(false);

  const fetchEmployees = useCallback(async () => {
    try {
      setLoading(true);
      const params = new URLSearchParams({
        page: page.toString(),
        page_size: pageSize.toString(),
        sort_by: sortBy,
        sort_order: sortOrder,
      });

      if (search.trim()) params.append('search', search.trim());
      if (statusFilter.trim()) params.append('status', statusFilter.trim());
      if (feedbackStatusFilter.trim()) params.append('feedback_status', feedbackStatusFilter.trim());

      const res = await api.get(`/employees?${params.toString()}`);
      setEmployees(res.data.items);
      setTotal(res.data.total);
      setTotalPages(res.data.total_pages);

      // Fetch email jobs for listed employees in parallel
      const jobsMap = {};
      await Promise.all(
        res.data.items.map(async (emp) => {
          try {
            const historyRes = await api.get(`/employees/${emp.id}/email-history`);
            if (historyRes.data && historyRes.data.length > 0) {
              jobsMap[emp.id] = historyRes.data[0].status;
            }
          } catch {
            // ignore
          }
        })
      );
      setEmailJobsMap(jobsMap);

      setError(null);
    } catch (err) {
      setError(err.message || 'Failed to fetch employee list');
    } finally {
      setLoading(false);
    }
  }, [page, pageSize, search, statusFilter, feedbackStatusFilter, sortBy, sortOrder]);

  useEffect(() => {
    fetchEmployees();
  }, [fetchEmployees]);

  const handleSort = (field) => {
    if (sortBy === field) {
      setSortOrder(sortOrder === 'asc' ? 'desc' : 'asc');
    } else {
      setSortBy(field);
      setSortOrder('asc');
    }
    setPage(1);
  };

  const handleDownloadTemplate = async () => {
    try {
      const response = await api.get('/employees/excel-template', {
        responseType: 'blob',
      });
      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', 'Exit_Feedback_Import_Template.xlsx');
      document.body.appendChild(link);
      link.click();
      link.remove();
    } catch {
      alert('Failed to download Excel template');
    }
  };

  const handleCancelClick = (emp) => {
    setSelectedEmployee(emp);
    setCancelModalOpen(true);
  };

  const handleConfirmCancel = async () => {
    if (!selectedEmployee) return;
    try {
      await api.post(`/employees/${selectedEmployee.id}/cancel`);
      fetchEmployees();
    } catch (err) {
      alert(err.message || 'Failed to cancel employee schedule');
    }
  };

  return (
    <div className="space-y-6">
      {/* Header Bar */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-extrabold text-white tracking-tight">Employee Exit Directory</h1>
          <p className="text-xs text-slate-400 mt-1">Manage exiting employee records and automated email feedback schedules</p>
        </div>
        <div className="flex items-center gap-3 shrink-0">
          <button
            onClick={handleDownloadTemplate}
            className="inline-flex items-center gap-2 px-3.5 py-2.5 bg-slate-900 hover:bg-slate-800 text-sky-400 text-xs font-semibold rounded-xl border border-slate-800 transition"
          >
            <Download className="w-4 h-4" />
            Download Excel Template
          </button>
          <button
            onClick={() => setExcelModalOpen(true)}
            className="inline-flex items-center gap-2 px-4 py-2.5 bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-bold rounded-xl shadow-lg shadow-emerald-950/40 transition"
          >
            <FileSpreadsheet className="w-4 h-4" />
            Import Excel
          </button>
          <Link
            to="/employees/new"
            className="inline-flex items-center gap-2 px-4 py-2.5 bg-gradient-to-r from-sky-600 to-cyan-600 hover:from-sky-500 hover:to-cyan-500 text-white text-xs font-bold rounded-xl shadow-lg shadow-sky-900/30 transition"
          >
            <UserPlus className="w-4 h-4" />
            Add Employee
          </Link>
        </div>
      </div>

      {/* Filter and Search Bar */}
      <div className="p-4 bg-slate-900/80 border border-slate-800 rounded-2xl shadow-lg space-y-3 md:space-y-0 md:flex md:items-center md:gap-4">
        {/* Search Input */}
        <div className="relative flex-1">
          <Search className="w-4 h-4 text-slate-500 absolute left-3.5 top-1/2 -translate-y-1/2" />
          <input
            type="text"
            value={search}
            onChange={(e) => {
              setSearch(e.target.value);
              setPage(1);
            }}
            placeholder="Search by Full Name or Personal Email..."
            className="w-full pl-10 pr-4 py-2 bg-slate-950/70 border border-slate-800 rounded-xl text-xs text-white placeholder-slate-500 focus:outline-none focus:border-sky-500 transition"
          />
        </div>

        {/* Filter Dropdowns */}
        <div className="flex items-center gap-3">
          <div className="relative min-w-[130px]">
            <select
              value={statusFilter}
              onChange={(e) => {
                setStatusFilter(e.target.value);
                setPage(1);
              }}
              className="w-full px-3 py-2 bg-slate-950/70 border border-slate-800 rounded-xl text-xs text-slate-200 focus:outline-none focus:border-sky-500 transition cursor-pointer"
            >
              <option value="">Employee Status</option>
              <option value="SCHEDULED">SCHEDULED</option>
              <option value="CANCELLED">CANCELLED</option>
            </select>
          </div>

          <div className="relative min-w-[140px]">
            <select
              value={feedbackStatusFilter}
              onChange={(e) => {
                setFeedbackStatusFilter(e.target.value);
                setPage(1);
              }}
              className="w-full px-3 py-2 bg-slate-950/70 border border-slate-800 rounded-xl text-xs text-slate-200 focus:outline-none focus:border-indigo-500 transition cursor-pointer"
            >
              <option value="">Feedback Status</option>
              <option value="PENDING">PENDING</option>
              <option value="SUBMITTED">SUBMITTED</option>
              <option value="EXPIRED">EXPIRED</option>
            </select>
          </div>
        </div>
      </div>

      {/* Error Alert */}
      {error && (
        <div className="p-4 bg-rose-500/10 border border-rose-500/30 rounded-2xl flex items-center gap-3 text-rose-400 text-sm">
          <AlertCircle className="w-5 h-5 shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {/* Table Card */}
      <div className="bg-slate-900/80 border border-slate-800 rounded-2xl shadow-xl overflow-hidden">
        {loading ? (
          <div className="p-12 flex justify-center items-center">
            <div className="animate-spin rounded-full h-8 w-8 border-t-2 border-b-2 border-sky-500" />
          </div>
        ) : employees.length === 0 ? (
          <div className="p-12 text-center text-slate-500 text-sm">
            No employees match your search or filter criteria.
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs border-collapse">
              <thead>
                <tr className="bg-slate-950/60 text-slate-400 font-semibold uppercase tracking-wider border-b border-slate-800">
                  <th className="py-3.5 px-5">
                    <button
                      onClick={() => handleSort('full_name')}
                      className="inline-flex items-center gap-1 hover:text-white transition"
                    >
                      Full Name
                      <ArrowUpDown className="w-3 h-3 text-slate-500" />
                    </button>
                  </th>
                  <th className="py-3.5 px-5">Personal Email</th>
                  <th className="py-3.5 px-5">
                    <button
                      onClick={() => handleSort('last_working_date')}
                      className="inline-flex items-center gap-1 hover:text-white transition"
                    >
                      Last Working Date
                      <ArrowUpDown className="w-3 h-3 text-slate-500" />
                    </button>
                  </th>
                  <th className="py-3.5 px-5">
                    <button
                      onClick={() => handleSort('feedback_due_date')}
                      className="inline-flex items-center gap-1 hover:text-white transition"
                    >
                      Feedback Due Date
                      <ArrowUpDown className="w-3 h-3 text-slate-500" />
                    </button>
                  </th>
                  <th className="py-3.5 px-5">Feedback Status</th>
                  <th className="py-3.5 px-5">Employee Status</th>
                  <th className="py-3.5 px-5">Email Status</th>
                  <th className="py-3.5 px-5 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/60 text-slate-300">
                {employees.map((emp) => (
                  <tr key={emp.id} className="hover:bg-slate-800/40 transition">
                    <td className="py-3.5 px-5 font-semibold text-white">{emp.full_name || emp.employee_name}</td>
                    <td className="py-3.5 px-5 text-slate-400 font-mono text-[11px]">{emp.personal_email}</td>
                    <td className="py-3.5 px-5 font-medium text-slate-200">{emp.last_working_date}</td>
                    <td className="py-3.5 px-5 font-semibold text-amber-300">{emp.feedback_due_date}</td>
                    <td className="py-3.5 px-5">
                      <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-[10px] font-semibold border ${
                        emp.feedback_status === 'SUBMITTED'
                          ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20'
                          : emp.feedback_status === 'EXPIRED'
                          ? 'bg-slate-500/10 text-slate-400 border-slate-500/20'
                          : 'bg-amber-500/10 text-amber-400 border-amber-500/20'
                      }`}>
                        {emp.feedback_status || 'PENDING'}
                      </span>
                    </td>
                    <td className="py-3.5 px-5">
                      <StatusBadge status={emp.status} />
                    </td>
                    <td className="py-3.5 px-5">
                      <EmailStatusBadge status={emailJobsMap[emp.id] || 'SCHEDULED'} />
                    </td>

                    <td className="py-3.5 px-5 text-right">
                      <div className="inline-flex items-center gap-1.5">
                        <Link
                          to={`/employees/${emp.id}`}
                          title="View Employee Details & Email History"
                          className="p-1.5 rounded-lg text-slate-400 hover:text-sky-400 hover:bg-sky-500/10 transition"
                        >
                          <Eye className="w-4 h-4" />
                        </Link>
                        <Link
                          to={`/employees/${emp.id}/edit`}
                          title="Edit Employee"
                          className="p-1.5 rounded-lg text-slate-400 hover:text-amber-400 hover:bg-amber-500/10 transition"
                        >
                          <Edit3 className="w-4 h-4" />
                        </Link>
                        {emp.status === 'SCHEDULED' && (
                          <button
                            onClick={() => handleCancelClick(emp)}
                            title="Cancel Schedule"
                            className="p-1.5 rounded-lg text-slate-400 hover:text-rose-400 hover:bg-rose-500/10 transition"
                          >
                            <Ban className="w-4 h-4" />
                          </button>
                        )}
                      </div>
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

      {/* Cancellation Confirmation Modal */}
      <Modal
        isOpen={cancelModalOpen}
        onClose={() => {
          setCancelModalOpen(false);
          setSelectedEmployee(null);
        }}
        onConfirm={handleConfirmCancel}
        title="Cancel Feedback Schedule"
        message={`Are you sure you want to cancel the feedback schedule for ${selectedEmployee?.full_name || selectedEmployee?.employee_name}? The record will remain in the database marked as CANCELLED.`}
        confirmText="Cancel Schedule"
        isDangerous={true}
      />

      {/* Excel Import Modal */}
      <ExcelImportModal
        isOpen={excelModalOpen}
        onClose={() => setExcelModalOpen(false)}
        onSuccess={() => {
          fetchEmployees();
        }}
      />
    </div>
  );
};

export default EmployeesPage;
