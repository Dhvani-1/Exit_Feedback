import React, { useState } from 'react';
import { X, Upload, Download, CheckCircle, AlertTriangle, AlertCircle, FileSpreadsheet, Loader2, RefreshCw } from 'lucide-react';
import api from '../../services/api';

const ExcelImportModal = ({ isOpen, onClose, onSuccess }) => {
  const [step, setStep] = useState('upload'); // 'upload' | 'preview' | 'summary'
  const [selectedFile, setSelectedFile] = useState(null);
  const [uploading, setUploading] = useState(false);
  const [importing, setImporting] = useState(false);
  const [downloadingError, setDownloadingError] = useState(false);
  const [error, setError] = useState('');

  const [previewData, setPreviewData] = useState(null);
  const [summaryData, setSummaryData] = useState(null);

  if (!isOpen) return null;

  const handleReset = () => {
    setStep('upload');
    setSelectedFile(null);
    setUploading(false);
    setImporting(false);
    setError('');
    setPreviewData(null);
    setSummaryData(null);
  };

  const handleClose = () => {
    handleReset();
    onClose();
  };

  const handleFileChange = (e) => {
    if (e.target.files && e.target.files[0]) {
      setSelectedFile(e.target.files[0]);
      setError('');
    }
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
      setError('Failed to download template file');
    }
  };

  const handleUploadPreview = async () => {
    if (!selectedFile) {
      setError('Please select an Excel file to upload.');
      return;
    }

    setUploading(true);
    setError('');

    const formData = new FormData();
    formData.append('file', selectedFile);

    try {
      const res = await api.post('/employees/upload-preview', formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
      });
      setPreviewData(res.data);
      setStep('preview');
    } catch (err) {
      setError(err.message || 'Failed to parse and validate Excel file');
    } finally {
      setUploading(false);
    }
  };

  const handleConfirmImport = async () => {
    if (!previewData || !previewData.valid_rows) return;

    setImporting(true);
    setError('');

    try {
      const res = await api.post('/employees/import-confirm', {
        valid_rows: previewData.valid_rows,
      });
      setSummaryData(res.data);
      setStep('summary');
      if (onSuccess) onSuccess();
    } catch (err) {
      setError(err.message || 'Failed to execute import');
    } finally {
      setImporting(false);
    }
  };

  const handleDownloadErrorReport = async () => {
    if (!previewData || !previewData.invalid_rows || previewData.invalid_rows.length === 0) return;

    setDownloadingError(true);
    try {
      const response = await api.post(
        '/employees/export-error-report',
        { invalid_rows: previewData.invalid_rows },
        { responseType: 'blob' }
      );
      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', 'Import_Error_Report.xlsx');
      document.body.appendChild(link);
      link.click();
      link.remove();
    } catch {
      setError('Failed to download error report');
    } finally {
      setDownloadingError(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-sm animate-fadeIn">
      <div className="bg-slate-900 border border-slate-800 rounded-3xl max-w-3xl w-full max-h-[90vh] flex flex-col shadow-2xl overflow-hidden">
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b border-slate-800">
          <div className="flex items-center gap-3">
            <div className="p-2.5 bg-emerald-500/10 text-emerald-400 rounded-2xl border border-emerald-500/20">
              <FileSpreadsheet className="w-5 h-5" />
            </div>
            <div>
              <h2 className="text-lg font-bold text-white">Import Employees via Excel</h2>
              <p className="text-xs text-slate-400">Batch upload exiting employee records</p>
            </div>
          </div>
          <button
            onClick={handleClose}
            className="p-2 text-slate-400 hover:text-white rounded-xl hover:bg-slate-800 transition"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Content Body */}
        <div className="p-6 overflow-y-auto space-y-6 flex-1">
          {error && (
            <div className="p-4 bg-rose-500/10 border border-rose-500/30 rounded-2xl flex items-center gap-3 text-rose-400 text-sm">
              <AlertCircle className="w-5 h-5 shrink-0" />
              <span>{error}</span>
            </div>
          )}

          {/* STEP 1: UPLOAD */}
          {step === 'upload' && (
            <div className="space-y-6">
              <div className="p-4 bg-slate-950/50 border border-slate-800 rounded-2xl flex items-center justify-between">
                <div>
                  <div className="text-sm font-semibold text-white">Excel File Template</div>
                  <div className="text-xs text-slate-400 mt-0.5">
                    Download the standard 3-column template (Full Name, Personal Email, Last Working Date)
                  </div>
                </div>
                <button
                  onClick={handleDownloadTemplate}
                  className="inline-flex items-center gap-2 px-3.5 py-2 bg-slate-800 hover:bg-slate-700 text-sky-400 text-xs font-bold rounded-xl border border-slate-700 transition"
                >
                  <Download className="w-4 h-4" />
                  Download Template
                </button>
              </div>

              {/* Dropzone */}
              <div className="border-2 border-dashed border-slate-800 hover:border-sky-500/50 rounded-3xl p-8 text-center bg-slate-950/30 transition">
                <input
                  type="file"
                  accept=".xlsx, .xls"
                  onChange={handleFileChange}
                  className="hidden"
                  id="excel-file-input"
                />
                <label htmlFor="excel-file-input" className="cursor-pointer block space-y-3">
                  <div className="w-12 h-12 rounded-2xl bg-sky-500/10 text-sky-400 mx-auto flex items-center justify-center border border-sky-500/20">
                    <Upload className="w-6 h-6" />
                  </div>
                  <div>
                    <span className="text-sm font-semibold text-sky-400">Click to select file</span>
                    <span className="text-sm text-slate-400"> or drag and drop</span>
                  </div>
                  <p className="text-xs text-slate-500">Supports .xlsx and .xls formats up to 5MB</p>
                </label>

                {selectedFile && (
                  <div className="mt-4 p-3 bg-sky-950/40 border border-sky-800/60 rounded-xl inline-flex items-center gap-3 text-xs text-sky-300 font-mono">
                    <FileSpreadsheet className="w-4 h-4" />
                    <span>{selectedFile.name} ({(selectedFile.size / 1024).toFixed(1)} KB)</span>
                  </div>
                )}
              </div>
            </div>
          )}

          {/* STEP 2: PREVIEW & VALIDATION */}
          {step === 'preview' && previewData && (
            <div className="space-y-6">
              {/* Metrics Summary Cards */}
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                <div className="p-3.5 bg-slate-950/60 border border-slate-800 rounded-2xl text-center">
                  <div className="text-xs text-slate-400">Total Rows</div>
                  <div className="text-xl font-extrabold text-white mt-1 font-mono">{previewData.total_rows}</div>
                </div>
                <div className="p-3.5 bg-emerald-950/30 border border-emerald-800/40 rounded-2xl text-center">
                  <div className="text-xs text-emerald-400">Valid Rows</div>
                  <div className="text-xl font-extrabold text-emerald-400 mt-1 font-mono">{previewData.valid_count}</div>
                </div>
                <div className="p-3.5 bg-amber-950/30 border border-amber-800/40 rounded-2xl text-center">
                  <div className="text-xs text-amber-400">Skipped Duplicates</div>
                  <div className="text-xl font-extrabold text-amber-400 mt-1 font-mono">{previewData.duplicate_count}</div>
                </div>
                <div className="p-3.5 bg-rose-950/30 border border-rose-800/40 rounded-2xl text-center">
                  <div className="text-xs text-rose-400">Invalid Rows</div>
                  <div className="text-xl font-extrabold text-rose-400 mt-1 font-mono">{previewData.invalid_count}</div>
                </div>
              </div>

              {/* Invalid Rows Table */}
              {previewData.invalid_rows && previewData.invalid_rows.length > 0 && (
                <div className="space-y-3">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2 text-rose-400 text-xs font-semibold uppercase tracking-wider">
                      <AlertTriangle className="w-4 h-4" />
                      <span>Invalid Rows Requiring Attention ({previewData.invalid_rows.length})</span>
                    </div>
                    <button
                      onClick={handleDownloadErrorReport}
                      disabled={downloadingError}
                      className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-rose-500/10 hover:bg-rose-500/20 text-rose-400 text-xs font-semibold rounded-xl border border-rose-500/30 transition disabled:opacity-50"
                    >
                      <Download className="w-3.5 h-3.5" />
                      Download Error Log (.xlsx)
                    </button>
                  </div>

                  <div className="border border-slate-800 rounded-2xl overflow-hidden max-h-56 overflow-y-auto">
                    <table className="w-full text-left text-xs">
                      <thead className="bg-slate-950 text-slate-400 font-semibold border-b border-slate-800 sticky top-0">
                        <tr>
                          <th className="py-2.5 px-3 w-16">Row #</th>
                          <th className="py-2.5 px-3">Full Name</th>
                          <th className="py-2.5 px-3">Personal Email</th>
                          <th className="py-2.5 px-3">Error Reason</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-slate-800/60 text-slate-300">
                        {previewData.invalid_rows.map((row, idx) => (
                          <tr key={idx} className="hover:bg-slate-950/40">
                            <td className="py-2 px-3 font-mono text-slate-400">{row.row_number}</td>
                            <td className="py-2 px-3">{row.full_name || '—'}</td>
                            <td className="py-2 px-3 font-mono text-slate-400">{row.personal_email || '—'}</td>
                            <td className="py-2 px-3 text-rose-400 font-medium">{row.error_reason}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              )}
            </div>
          )}

          {/* STEP 3: SUMMARY */}
          {step === 'summary' && summaryData && (
            <div className="text-center py-6 space-y-4">
              <div className="w-16 h-16 rounded-full bg-emerald-500/10 text-emerald-400 mx-auto flex items-center justify-center border border-emerald-500/20">
                <CheckCircle className="w-8 h-8" />
              </div>
              <div>
                <h3 className="text-xl font-bold text-white">Import Completed Successfully</h3>
                <p className="text-xs text-slate-400 mt-1">Processed {summaryData.total_processed} rows</p>
              </div>

              <div className="grid grid-cols-2 gap-4 max-w-md mx-auto pt-2">
                <div className="p-4 bg-slate-950/60 border border-slate-800 rounded-2xl">
                  <div className="text-xs text-slate-400">Successfully Imported</div>
                  <div className="text-2xl font-extrabold text-emerald-400 mt-1 font-mono">{summaryData.imported_count}</div>
                </div>
                <div className="p-4 bg-slate-950/60 border border-slate-800 rounded-2xl">
                  <div className="text-xs text-slate-400">Skipped Duplicates</div>
                  <div className="text-2xl font-extrabold text-amber-400 mt-1 font-mono">{summaryData.skipped_duplicates_count}</div>
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Modal Footer Controls */}
        <div className="p-6 border-t border-slate-800 flex items-center justify-between bg-slate-950/40">
          {step === 'upload' && (
            <>
              <button
                type="button"
                onClick={handleClose}
                className="px-4 py-2 text-xs font-semibold text-slate-400 hover:text-white"
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={handleUploadPreview}
                disabled={!selectedFile || uploading}
                className="inline-flex items-center gap-2 px-5 py-2.5 bg-gradient-to-r from-sky-600 to-cyan-600 hover:from-sky-500 hover:to-cyan-500 text-white text-xs font-bold rounded-xl shadow-lg shadow-sky-900/30 transition disabled:opacity-50"
              >
                {uploading ? (
                  <>
                    <Loader2 className="w-4 h-4 animate-spin" />
                    Parsing & Validating...
                  </>
                ) : (
                  'Validate & Preview'
                )}
              </button>
            </>
          )}

          {step === 'preview' && (
            <>
              <button
                type="button"
                onClick={handleReset}
                className="inline-flex items-center gap-1.5 px-4 py-2 text-xs font-semibold text-slate-400 hover:text-white bg-slate-800 rounded-xl transition"
              >
                <RefreshCw className="w-3.5 h-3.5" />
                Upload Different File
              </button>
              <button
                type="button"
                onClick={handleConfirmImport}
                disabled={importing || (previewData && previewData.valid_count === 0)}
                className="inline-flex items-center gap-2 px-5 py-2.5 bg-gradient-to-r from-emerald-600 to-teal-600 hover:from-emerald-500 hover:to-teal-500 text-white text-xs font-bold rounded-xl shadow-lg shadow-emerald-900/30 transition disabled:opacity-50"
              >
                {importing ? (
                  <>
                    <Loader2 className="w-4 h-4 animate-spin" />
                    Importing Records...
                  </>
                ) : (
                  `Confirm Import (${previewData ? previewData.valid_count - previewData.duplicate_count : 0} New)`
                )}
              </button>
            </>
          )}

          {step === 'summary' && (
            <div className="w-full flex justify-end">
              <button
                type="button"
                onClick={handleClose}
                className="px-6 py-2.5 bg-sky-600 hover:bg-sky-500 text-white text-xs font-bold rounded-xl shadow-lg shadow-sky-900/30 transition"
              >
                Done
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default ExcelImportModal;
