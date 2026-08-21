import axios from 'axios';

const rawApiUrl = import.meta.env.VITE_API_URL;
let baseURL = '/api';
if (rawApiUrl) {
  if (rawApiUrl.startsWith('http://') || rawApiUrl.startsWith('https://')) {
    baseURL = rawApiUrl.endsWith('/api') ? rawApiUrl : `${rawApiUrl}/api`;
  } else {
    baseURL = `https://${rawApiUrl}/api`;
  }
}

const api = axios.create({
  baseURL: baseURL,
  withCredentials: true,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Interceptor to parse standardized error messages
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response && error.response.data) {
      const data = error.response.data;
      let errMsg = 'An error occurred';
      let errCode = 'ERROR';
      let errDetails = null;

      if (data.error) {
        errMsg = data.error.message || errMsg;
        errCode = data.error.code || errCode;
        errDetails = data.error.details || null;
      } else if (data.detail) {
        errMsg = typeof data.detail === 'string' ? data.detail : JSON.stringify(data.detail);
      }

      const customErr = new Error(errMsg);
      customErr.code = errCode;
      customErr.details = errDetails;
      customErr.status = error.response.status;
      return Promise.reject(customErr);
    }
    return Promise.reject(error);
  }
);

export default api;
