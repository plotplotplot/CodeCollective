// Initialize Keycloak
const keycloak = new Keycloak({
  url: 'https://keycloak.app.codecollective.us/auth',
  realm: 'opentdf',
  clientId: 'web-client'
});

// Initialize authentication
function initAuth() {
  keycloak.init({ onLoad: 'check-sso' })
    .then(authenticated => {
      updateUI(authenticated);
    })
    .catch(err => {
      console.error('Keycloak initialization failed', err);
    });
}

// Update UI based on auth state
function updateUI(authenticated) {
  const loginBtn = document.getElementById('login-btn');
  
  if (authenticated) {
    // User is logged in - show profile picture
    loginBtn.innerHTML = `
      <img src="${keycloak.tokenParsed?.picture || 'default-profile.png'}" 
           class="profile-pic" 
           alt="Profile">
    `;
    loginBtn.href = './profile.html';
  } else {
    // User not logged in - show login button
    loginBtn.innerHTML = 'Login';
    loginBtn.href = '#';
    loginBtn.onclick = () => keycloak.login();
  }
}

// Initialize when DOM is loaded
document.addEventListener('DOMContentLoaded', initAuth);
