/**
 * Authentication module for Enterprise Agent POC
 */
(function() {
  'use strict';

  // State
  let currentUser = null;
  let loginModal = null;

  // Initialize on DOM ready
  document.addEventListener('DOMContentLoaded', function() {
    initAuth();
  });

  function initAuth() {
    // Initialize Bootstrap modal
    const modalEl = document.getElementById('login-modal');
    if (modalEl) {
      loginModal = new bootstrap.Modal(modalEl);
    }

    // Check if user is logged in
    checkAuthStatus();

    // Setup event listeners
    setupEventListeners();
  }

  function setupEventListeners() {
    // Login form submission
    const loginForm = document.getElementById('login-form');
    if (loginForm) {
      loginForm.addEventListener('submit', handleLogin);
    }

    // Logout button
    const logoutBtn = document.getElementById('logout-btn');
    if (logoutBtn) {
      logoutBtn.addEventListener('click', handleLogout);
    }
  }

  async function checkAuthStatus() {
    try {
      const response = await fetch('/api/auth/me', {
        credentials: 'include'
      });

      if (response.ok) {
        const data = await response.json();
        if (data.status === 'success' && data.user) {
          setLoggedIn(data.user);
          return;
        }
      }

      // Not logged in, show login modal
      showLoginModal();
    } catch (error) {
      console.error('Auth check failed:', error);
      showLoginModal();
    }
  }

  async function handleLogin(event) {
    event.preventDefault();

    const username = document.getElementById('login-username').value.trim();
    const password = document.getElementById('login-password').value;
    const errorEl = document.getElementById('login-error');

    // Clear previous error
    errorEl.classList.add('d-none');
    errorEl.textContent = '';

    try {
      const response = await fetch('/api/auth/login', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        credentials: 'include',
        body: JSON.stringify({ username, password })
      });

      const data = await response.json();

      if (response.ok && data.status === 'success') {
        setLoggedIn(data.user);
        hideLoginModal();
        // Store token for API calls
        if (data.token) {
          localStorage.setItem('session_token', data.token);
        }
      } else {
        showLoginError(data.error || '登入失敗');
      }
    } catch (error) {
      console.error('Login failed:', error);
      showLoginError('網路錯誤，請稍後再試');
    }
  }

  async function handleLogout() {
    try {
      await fetch('/api/auth/logout', {
        method: 'POST',
        credentials: 'include'
      });
    } catch (error) {
      console.error('Logout failed:', error);
    }

    // Clear local state
    currentUser = null;
    localStorage.removeItem('session_token');

    // Update UI
    setLoggedOut();
    showLoginModal();
  }

  function setLoggedIn(user) {
    currentUser = user;

    // Update UI elements
    const userInfo = document.getElementById('user-info');
    const displayName = document.getElementById('user-display-name');
    const roleBadge = document.getElementById('user-role-badge');
    const userDivider = document.getElementById('user-divider');

    if (userInfo) {
      userInfo.classList.remove('d-none');
    }

    if (displayName) {
      displayName.textContent = user.display_name || user.username;
    }

    if (roleBadge) {
      roleBadge.textContent = user.role === 'admin' ? '管理員' : '使用者';
      roleBadge.className = user.role === 'admin'
        ? 'badge bg-danger me-2'
        : 'badge bg-secondary me-2';
    }

    if (userDivider) {
      userDivider.style.display = 'block';
    }

    // Dispatch custom event for other modules
    document.dispatchEvent(new CustomEvent('userLoggedIn', { detail: user }));
  }

  function setLoggedOut() {
    const userInfo = document.getElementById('user-info');
    const userDivider = document.getElementById('user-divider');

    if (userInfo) {
      userInfo.classList.add('d-none');
    }

    if (userDivider) {
      userDivider.style.display = 'none';
    }

    // Dispatch custom event
    document.dispatchEvent(new CustomEvent('userLoggedOut'));
  }

  function showLoginModal() {
    if (loginModal) {
      loginModal.show();
    }
  }

  function hideLoginModal() {
    if (loginModal) {
      loginModal.hide();
    }
    // Clear form
    const loginForm = document.getElementById('login-form');
    if (loginForm) {
      loginForm.reset();
    }
  }

  function showLoginError(message) {
    const errorEl = document.getElementById('login-error');
    if (errorEl) {
      errorEl.textContent = message;
      errorEl.classList.remove('d-none');
    }
  }

  // Export for global access
  window.EnterpriseAuth = {
    getCurrentUser: function() { return currentUser; },
    isLoggedIn: function() { return currentUser !== null; },
    isAdmin: function() { return currentUser && currentUser.role === 'admin'; },
    logout: handleLogout
  };
})();
