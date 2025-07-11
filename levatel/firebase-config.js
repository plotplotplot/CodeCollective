// Firebase configuration and auth
import { initializeApp } from "https://www.gstatic.com/firebasejs/11.10.0/firebase-app.js";
import { getAuth, signOut, onAuthStateChanged, GoogleAuthProvider, GithubAuthProvider, signInWithPopup, linkWithCredential, EmailAuthProvider, fetchSignInMethodsForEmail } from "https://www.gstatic.com/firebasejs/11.10.0/firebase-auth.js";
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
    const loginContainer = document.getElementById('loginContainer');
    const body = document.getElementById('body');

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


// Unified auth handler
async function handleAuthSignIn(provider, errorProvider) {
    try {
        console.log("Attempting sign-in with provider:", provider.providerId);
        const result = await signInWithPopup(auth, provider);
        console.log("Sign-in successful, redirecting...");
        window.location.href = "index.html";
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

// Handle auth button clicks
document.addEventListener('DOMContentLoaded', () => {
    // Google sign-in
    const googleSignInBtn = document.getElementById('googleSignIn');
    if (googleSignInBtn) {
        googleSignInBtn.addEventListener('click', () => {
            handleAuthSignIn(googleProvider, GoogleAuthProvider);
        });
    }

    // GitHub sign-in
    const githubSignInBtn = document.getElementById('githubSignIn');
    if (githubSignInBtn) {
        githubSignInBtn.addEventListener('click', () => {
            handleAuthSignIn(githubProvider, GithubAuthProvider);
        });
    }
});
