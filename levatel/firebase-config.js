// Firebase configuration and auth
import { initializeApp } from "https://www.gstatic.com/firebasejs/11.10.0/firebase-app.js";
import { getAuth, signOut, onAuthStateChanged, GoogleAuthProvider, GithubAuthProvider, signInWithPopup, signInWithRedirect, linkWithCredential, EmailAuthProvider, fetchSignInMethodsForEmail } from "https://www.gstatic.com/firebasejs/11.10.0/firebase-auth.js";
const googleProvider = new GoogleAuthProvider();
const githubProvider = new GithubAuthProvider();
// Add GitHub OAuth scope
githubProvider.addScope('read:user');
githubProvider.setCustomParameters({
  prompt: 'select_account'
});

export const firebaseConfig = {
    apiKey: "AIzaSyCS457zr9rpyORhefGcfvb4xZwsXXYg0Dc",
    authDomain: "levatel-d3b77.firebaseapp.com",
    projectId: "levatel-d3b77",
    storageBucket: "levatel-d3b77.firebasestorage.app",
    messagingSenderId: "922786354907",
    appId: "1:922786354907:web:bc01bf82b626ebc5875efe",
    measurementId: "G-5Z06BMPY2B"
};

// Import Firebase auth

// Initialize Firebase
export const app = initializeApp(firebaseConfig);
export const auth = getAuth(app);

// Unified auth state handler
onAuthStateChanged(auth, (user) => {
    const loginContainer = document.querySelector('.login-container');
    const body = document.body;

    if (user) {
        // User is logged in - hide login and show app
        if (window.location.pathname.includes('login.html')) {
            window.location.href = "index.html";
        }
        if (loginContainer) {
            loginContainer.style.display = 'none';
        }
        if (body) {
            body.classList.remove('logged-out');
        }
    } else {
        // User is logged out - show login page
        if (!window.location.pathname.includes('login.html')) {
            window.location.href = "login.html";
        }
        if (loginContainer) {
            loginContainer.style.display = 'block';
        }
        if (body) {
            body.classList.add('logged-out');
        }
    }
});

// Request webcam access - Uncomment for demos
/*
const webcam = document.getElementById('webcam');
if (navigator.mediaDevices && navigator.mediaDevices.getUserMedia) {
navigator.mediaDevices.getUserMedia({ video: true, audio: false })
    .then(stream => {
    webcam.srcObject = stream;
    })
    .catch(err => {
    console.error('Could not access webcam:', err);
    });
}
    */
    
// Auth functions
export const logout = async () => {
    try {
        await signOut(auth);
    } catch (error) {
        console.error('Logout error:', error);
        throw error;
    }
};


// Unified auth handler with popup fallback
async function handleAuthSignIn(provider, errorProvider) {
    try {
        console.log("Attempting sign-in with provider:", provider.providerId);
        
        // First try popup method
        try {
            const result = await signInWithPopup(auth, provider);
            console.log("Popup sign-in successful, redirecting...");
            window.location.href = "index.html";
            return;
        } catch (popupError) {
            console.log("Popup failed, trying redirect:", popupError);
            if (popupError.code === 'auth/popup-blocked' || popupError.code === 'auth/popup-closed-by-user') {
                // Fallback to redirect if popup is blocked or closed
                await signInWithRedirect(auth, provider);
                return;
            }
            throw popupError; // Re-throw other errors
        }
    } catch (error) {
        console.error("Full auth error:", error);
        if (error.code === 'auth/account-exists-with-different-credential') {
            try {
                console.log("Attempting account linking...");
                const email = error.customData.email;
                const providers = await fetchSignInMethodsForEmail(auth, email);
                
                if (providers.includes('google.com')) {
                    // Show message to user about account linking
                    alert(`Please sign in with Google to link your GitHub account (${email})`);
                    
                    try {
                        const result = await signInWithPopup(auth, googleProvider);
                        const credential = errorProvider.credentialFromError(error);
                        if (credential) {
                            console.log("Linking GitHub credential to existing account");
                            await linkWithCredential(result.user, credential);
                            alert("Accounts successfully linked!");
                            window.location.href = "index.html";
                        }
                    } catch (linkError) {
                        console.error("Linking process error:", linkError);
                        alert("Failed to link accounts. Please try again.");
                    }
                } else {
                    alert(`An account already exists for ${email} with a different provider`);
                }
            } catch (linkError) {
                console.error("Account linking error details:", {
                    error: linkError,
                    stack: linkError.stack
                });
                alert("An error occurred during account linking. Please try again.");
            }
        } else {
            console.error("Authentication error details:", {
                code: error.code,
                message: error.message,
                email: error.email,
                credential: error.credential
            });
        }
    }
}

// Handle auth button clicks and add alternative methods
document.addEventListener('DOMContentLoaded', () => {
    // Add popup blocker warning
    const popupWarning = document.createElement('div');
    popupWarning.className = 'popup-warning hidden';
    popupWarning.innerHTML = `
        <p>Popup blocked! Please allow popups for this site or use the redirect method below.</p>
        <button class="auth-button redirect-button">Sign in with Redirect</button>
    `;
    document.querySelector('.login-box')?.appendChild(popupWarning);

    // Google sign-in
    const googleSignInBtn = document.getElementById('googleSignIn');
    if (googleSignInBtn) {
        googleSignInBtn.addEventListener('click', async () => {
            try {
                await handleAuthSignIn(googleProvider, GoogleAuthProvider);
            } catch (error) {
                if (error.code === 'auth/popup-blocked') {
                    document.querySelector('.popup-warning').classList.remove('hidden');
                }
                console.error("Google sign-in error:", error);
            }
        });
    }

    // GitHub sign-in
    const githubSignInBtn = document.getElementById('githubSignIn');
    if (githubSignInBtn) {
        githubSignInBtn.addEventListener('click', async () => {
            try {
                await handleAuthSignIn(githubProvider, GithubAuthProvider);
            } catch (error) {
                if (error.code === 'auth/popup-blocked') {
                    document.querySelector('.popup-warning').classList.remove('hidden');
                }
                console.error("GitHub sign-in error:", error);
            }
        });
    }

    // Handle redirect button clicks
    document.addEventListener('click', (e) => {
        if (e.target.classList.contains('redirect-button')) {
            const provider = e.target.closest('.popup-warning').previousElementSibling?.id === 'googleSignIn' 
                ? googleProvider 
                : githubProvider;
            signInWithRedirect(auth, provider);
        }
    });
});
