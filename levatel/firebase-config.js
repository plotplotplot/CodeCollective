// Firebase configuration and auth
import { initializeApp } from "https://www.gstatic.com/firebasejs/11.10.0/firebase-app.js";
import { getAuth, signOut } from "https://www.gstatic.com/firebasejs/11.10.0/firebase-auth.js";

export const firebaseConfig = {
    apiKey: "AIzaSyCS457zr9rpyORhefGcfvb4xZwsXXYg0Dc",
    authDomain: "levatel-d3b77.firebaseapp.com",
    projectId: "levatel-d3b77",
    storageBucket: "levatel-d3b77.firebasestorage.app",
    messagingSenderId: "922786354907",
    appId: "1:922786354907:web:bc01bf82b626ebc5875efe",
    measurementId: "G-5Z06BMPY2B"
};

// Initialize Firebase
const app = initializeApp(firebaseConfig);
export const auth = getAuth(app);

// Auth functions
export const logout = async () => {
    try {
        await signOut(auth);
    } catch (error) {
        console.error('Logout error:', error);
        throw error;
    }
};
