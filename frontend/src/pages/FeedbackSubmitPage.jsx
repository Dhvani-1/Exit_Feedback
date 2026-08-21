import React, { useEffect, useState } from 'react';
import { useParams } from 'react-router-dom';
import axios from 'axios';
import { CheckCircle2, AlertCircle, Clock, FileText, Send, Building2 } from 'lucide-react';

const FeedbackSubmitPage = () => {
  const { token } = useParams();
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [feedbackData, setFeedbackData] = useState(null);
  const [error, setError] = useState('');
  const [submittedSuccess, setSubmittedSuccess] = useState(false);

  useEffect(() => {
    const fetchStatus = async () => {
      try {
        setLoading(true);
        setError('');
        const res = await axios.get(`/api/feedback/${token}`);
        setFeedbackData(res.data);
      } catch (err) {
        const msg = err.response?.data?.error?.message || 'Invalid or expired feedback link.';
        setError(msg);
      } finally {
        setLoading(false);
      }
    };
    if (token) {
      fetchStatus();
    }
  }, [token]);

  const handleSubmit = async () => {
    try {
      setSubmitting(true);
      setError('');
      const res = await axios.post(`/api/feedback/${token}/submit`, {
        submission_source: 'CUSTOM_FORM',
      });
      setFeedbackData((prev) => ({
        ...prev,
        status: 'SUBMITTED',
        submitted_at: res.data.submitted_at,
      }));
      setSubmittedSuccess(true);
    } catch (err) {
      const msg = err.response?.data?.error?.message || 'Failed to submit feedback. Please try again.';
      setError(msg);
    } finally {
      setSubmitting(false);
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-slate-950 flex flex-col items-center justify-center text-slate-100 p-4">
        <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-indigo-500 mb-4" />
        <p className="text-slate-400 font-medium">Validating feedback link...</p>
      </div>
    );
  }

  if (error && !feedbackData) {
    return (
      <div className="min-h-screen bg-slate-950 flex items-center justify-center p-4">
        <div className="max-w-md w-full bg-slate-900 border border-slate-800 rounded-2xl p-8 text-center shadow-xl">
          <div className="w-16 h-16 bg-red-500/10 border border-red-500/20 text-red-400 rounded-2xl flex items-center justify-center mx-auto mb-4">
            <AlertCircle className="w-8 h-8" />
          </div>
          <h2 className="text-xl font-bold text-slate-100 mb-2">Invalid or Expired Link</h2>
          <p className="text-slate-400 text-sm mb-6">{error}</p>
          <div className="text-xs text-slate-500">
            If you believe this is an error, please contact your HR department.
          </div>
        </div>
      </div>
    );
  }

  const isSubmitted = feedbackData?.status === 'SUBMITTED' || submittedSuccess;
  const isExpired = feedbackData?.status === 'EXPIRED';

  return (
    <div className="min-h-screen bg-slate-950 flex flex-col items-center justify-center p-4">
      <div className="max-w-lg w-full bg-slate-900 border border-slate-800 rounded-2xl p-8 shadow-2xl relative overflow-hidden">
        {/* Decorative Top Gradient Bar */}
        <div className="absolute top-0 left-0 right-0 h-1.5 bg-gradient-to-r from-indigo-500 via-purple-500 to-pink-500" />

        {/* Company Header */}
        <div className="flex items-center space-x-3 mb-6 pb-6 border-b border-slate-800">
          <div className="w-10 h-10 bg-indigo-500/10 border border-indigo-500/20 rounded-xl flex items-center justify-center text-indigo-400">
            <Building2 className="w-5 h-5" />
          </div>
          <div>
            <h1 className="text-base font-bold text-slate-100">{feedbackData?.company_name || 'Company HR'}</h1>
            <p className="text-xs text-slate-400">Employee Exit Feedback Automation</p>
          </div>
        </div>

        {/* State 1: Submitted */}
        {isSubmitted && (
          <div className="text-center py-4">
            <div className="w-16 h-16 bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 rounded-2xl flex items-center justify-center mx-auto mb-4">
              <CheckCircle2 className="w-8 h-8" />
            </div>
            <h2 className="text-2xl font-bold text-slate-100 mb-2">Feedback Recorded</h2>
            <p className="text-slate-300 text-sm mb-4">
              Thank you, <span className="font-semibold text-indigo-400">{feedbackData?.employee_name}</span>! Your exit feedback has been successfully recorded.
            </p>
            {feedbackData?.submitted_at && (
              <p className="text-xs text-slate-500">
                Submitted on: {new Date(feedbackData.submitted_at).toLocaleString()}
              </p>
            )}
            <div className="mt-6 pt-6 border-t border-slate-800 text-xs text-slate-500">
              Your valuable feedback helps improve our workplace culture and processes. Future reminder notifications for this cycle have been automatically cancelled.
            </div>
          </div>
        )}

        {/* State 2: Expired */}
        {!isSubmitted && isExpired && (
          <div className="text-center py-4">
            <div className="w-16 h-16 bg-amber-500/10 border border-amber-500/20 text-amber-400 rounded-2xl flex items-center justify-center mx-auto mb-4">
              <Clock className="w-8 h-8" />
            </div>
            <h2 className="text-2xl font-bold text-slate-100 mb-2">Form Expired</h2>
            <p className="text-slate-300 text-sm mb-4">
              This feedback link for <span className="font-semibold text-amber-400">{feedbackData?.employee_name}</span> is no longer available.
            </p>
            <p className="text-xs text-slate-500">
              The feedback submission period has elapsed. Please reach out to HR if you still wish to submit feedback.
            </p>
          </div>
        )}

        {/* State 3: Pending Submission */}
        {!isSubmitted && !isExpired && (
          <div>
            <div className="mb-6">
              <span className="inline-flex items-center px-3 py-1 rounded-full text-xs font-medium bg-indigo-500/10 text-indigo-400 border border-indigo-500/20 mb-3">
                <FileText className="w-3.5 h-3.5 mr-1.5" /> Pending Submission
              </span>
              <h2 className="text-2xl font-bold text-slate-100 mb-2">Exit Feedback Questionnaire</h2>
              <p className="text-slate-400 text-sm">
                Dear <span className="text-slate-200 font-semibold">{feedbackData?.employee_name}</span>, please confirm your submission to complete your exit feedback process.
              </p>
            </div>

            {error && (
              <div className="mb-6 p-4 rounded-xl bg-red-500/10 border border-red-500/20 text-red-400 text-xs flex items-start space-x-2">
                <AlertCircle className="w-4 h-4 shrink-0 mt-0.5" />
                <span>{error}</span>
              </div>
            )}

            <div className="bg-slate-950/60 border border-slate-800 rounded-xl p-4 mb-6 space-y-2 text-xs text-slate-400">
              <div className="flex justify-between">
                <span>Status:</span>
                <span className="text-amber-400 font-semibold">Pending Response</span>
              </div>
              {feedbackData?.expires_at && (
                <div className="flex justify-between">
                  <span>Expires on:</span>
                  <span>{new Date(feedbackData.expires_at).toLocaleDateString()}</span>
                </div>
              )}
            </div>

            <button
              onClick={handleSubmit}
              disabled={submitting}
              className="w-full py-3.5 px-4 bg-indigo-600 hover:bg-indigo-500 active:bg-indigo-700 disabled:opacity-50 text-white font-semibold rounded-xl text-sm transition shadow-lg shadow-indigo-600/25 flex items-center justify-center space-x-2"
            >
              {submitting ? (
                <>
                  <div className="animate-spin rounded-full h-4 w-4 border-2 border-white border-t-transparent mr-2" />
                  <span>Submitting Feedback...</span>
                </>
              ) : (
                <>
                  <Send className="w-4 h-4" />
                  <span>Submit Exit Feedback</span>
                </>
              )}
            </button>

            <p className="mt-4 text-center text-xs text-slate-500">
              Submitting will automatically notify HR and turn off subsequent reminder emails.
            </p>
          </div>
        )}
      </div>
    </div>
  );
};

export default FeedbackSubmitPage;
