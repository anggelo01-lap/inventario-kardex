const host = typeof window !== 'undefined' ? window.location.hostname : '';
const isLocalHost = host === '127.0.0.1' || host === 'localhost';

export const environment = {
  production: false,
  apiUrl: isLocalHost ? 'http://127.0.0.1:8000/api/v1' : '/api/v1'
};
