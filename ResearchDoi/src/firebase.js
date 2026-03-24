import { initializeApp } from "firebase/app";
import { getAnalytics } from "firebase/analytics";
import { getAuth, GoogleAuthProvider } from "firebase/auth";
import { getFirestore } from "firebase/firestore";

// Your web app's Firebase configuration
const firebaseConfig = {
    apiKey: "REDACTED_API_KEYC3ET_pJZVkrZPZsQQ9SetW7Z4hcojjIz4",
    authDomain: "researchassistant-3446d.firebaseapp.com",
    projectId: "researchassistant-3446d",
    storageBucket: "researchassistant-3446d.firebasestorage.app",
    messagingSenderId: "881013919729",
    appId: "1:881013919729:web:129cdb460ed5429cbbbe50",
    measurementId: "G-NFXLWRWCFD"
};

// Initialize Firebase
const app = initializeApp(firebaseConfig);
const analytics = getAnalytics(app);
const auth = getAuth(app);
const db = getFirestore(app);
const googleProvider = new GoogleAuthProvider();

export { app, analytics, auth, db, googleProvider };
