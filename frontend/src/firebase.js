import { initializeApp } from 'firebase/app';
import {
  createUserWithEmailAndPassword,
  getAuth,
  onAuthStateChanged,
  signInWithEmailAndPassword,
  signOut,
} from 'firebase/auth';
import {
  collection,
  doc,
  getDoc,
  getDocs,
  getFirestore,
  limit,
  query,
  serverTimestamp,
  setDoc,
  where,
} from 'firebase/firestore';

// Firebase Web configuration is safe to ship to the browser. Access control
// must be enforced with Firebase Authentication and Firestore Security Rules.
const firebaseConfig = {
  apiKey: 'AIzaSyBzNmYtNA7Dlmi8PyV0_pGqcjM3ZHefoCA',
  authDomain: 'traffic-project-3295a.firebaseapp.com',
  projectId: 'traffic-project-3295a',
  storageBucket: 'traffic-project-3295a.firebasestorage.app',
  messagingSenderId: '568047712187',
  appId: '1:568047712187:web:eb69390d78098dccd0369e',
  measurementId: 'G-FQJMEFJZZX',
};

const app = initializeApp(firebaseConfig);

export const auth = getAuth(app);
export const db = getFirestore(app);

async function getProfile(firebaseUser) {
  const profileRef = doc(db, 'users', firebaseUser.uid);
  const profileSnapshot = await getDoc(profileRef);
  const profile = profileSnapshot.exists() ? profileSnapshot.data() : {};

  return {
    id: firebaseUser.uid,
    uid: firebaseUser.uid,
    username: profile.username || firebaseUser.displayName || firebaseUser.email?.split('@')[0] || 'user',
    email: profile.email || firebaseUser.email || '',
    full_name: profile.full_name || profile.username || firebaseUser.displayName || '',
    role: profile.role || 'user',
    business_id: profile.business_id ?? null,
    is_active: profile.is_active ?? true,
  };
}

async function resolveEmail(identifier) {
  if (identifier.includes('@')) return identifier.trim();

  const usernameQuery = query(
    collection(db, 'users'),
    where('username', '==', identifier.trim()),
    limit(1),
  );
  const result = await getDocs(usernameQuery);
  if (result.empty) {
    throw new Error('ไม่พบชื่อผู้ใช้หรืออีเมลนี้');
  }

  return result.docs[0].data().email;
}

export async function loginWithFirebase(identifier, password) {
  const email = await resolveEmail(identifier);
  const credentials = await signInWithEmailAndPassword(auth, email, password);
  return getProfile(credentials.user);
}

export async function registerWithFirebase({ username, email, password, fullName }) {
  const credentials = await createUserWithEmailAndPassword(auth, email.trim(), password);
  await setDoc(doc(db, 'users', credentials.user.uid), {
    username: username.trim(),
    email: email.trim(),
    full_name: fullName?.trim() || username.trim(),
    role: 'user',
    business_id: null,
    is_active: true,
    created_at: serverTimestamp(),
  });
  return getProfile(credentials.user);
}

export async function getCurrentUserProfile(firebaseUser) {
  return getProfile(firebaseUser);
}

export { onAuthStateChanged, signOut };
export default app;
