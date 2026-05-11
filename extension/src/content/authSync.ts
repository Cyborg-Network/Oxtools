const syncToken = () => {
  // Check for tokens in localStorage or cookies
  const token = localStorage.getItem("access_token") || localStorage.getItem("token") || getCookie("access_token");
  if (token) {
    chrome.storage.local.set({ access_token: token });
  }
};

function getCookie(name: string) {
  const value = `; ${document.cookie}`;
  const parts = value.split(`; ${name}=`);
  if (parts.length === 2) return parts.pop()?.split(';').shift();
  return null;
}

// Sync on load
syncToken();

// Optional: listen for storage changes on the page to sync live log-ins
window.addEventListener('storage', (e) => {
  if (e.key === 'access_token' || e.key === 'token') {
    syncToken();
  }
});
