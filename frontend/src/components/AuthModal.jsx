import React, { useState, useEffect } from 'react';
import { api } from '../services/api';
import { loginWithFirebase, registerWithFirebase, signOut, auth } from '../firebase';

export function AuthModal({ isOpen, onClose, currentUser, onLoginSuccess, onLogout }) {
  const [tab, setTab] = useState('login'); // 'login' | 'register'
  const [username, setUsername] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [fullName, setFullName] = useState('');
  const [role, setRole] = useState('business_owner');
  const [error, setError] = useState(null);
  const [isLoading, setIsLoading] = useState(false);
  const [demoAccounts, setDemoAccounts] = useState([]);

  useEffect(() => {
    async function loadDemoAccounts() {
      try {
        const res = await api.getDemoAccounts();
        if (res && res.accounts) {
          setDemoAccounts(res.accounts);
        }
      } catch (err) {
        // silent fallback
      }
    }
    if (isOpen) {
      loadDemoAccounts();
      setError(null);
    }
  }, [isOpen]);

  if (!isOpen) return null;

  const handleLogin = async (e) => {
    if (e) e.preventDefault();
    setError(null);
    setIsLoading(true);
    try {
      const user = await loginWithFirebase(username, password);
      onLoginSuccess(user);
      onClose();
    } catch (err) {
      setError(err.message || 'เข้าสู่ระบบไม่สำเร็จ กรุณาตรวจสอบข้อมูล');
    } finally {
      setIsLoading(false);
    }
  };

  const handleRegister = async (e) => {
    if (e) e.preventDefault();
    setError(null);
    setIsLoading(true);
    try {
      const user = await registerWithFirebase({
        username,
        email,
        password,
        full_name: fullName,
      });
      onLoginSuccess(user);
      onClose();
    } catch (err) {
      setError(err.message || 'สมัครสมาชิกไม่สำเร็จ');
    } finally {
      setIsLoading(false);
    }
  };

  const handleQuickDemoLogin = async (acc) => {
    setUsername(acc.username);
    setPassword(acc.password);
    setError(null);
    setIsLoading(true);
    try {
      const user = await loginWithFirebase(acc.username, acc.password);
      onLoginSuccess(user);
      onClose();
    } catch (err) {
      setError(err.message || 'เข้าสู่ระบบด้วยบัญชีทดสอบไม่สำเร็จ');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div style={{
      position: 'fixed',
      top: 0,
      left: 0,
      right: 0,
      bottom: 0,
      backgroundColor: 'rgba(0, 0, 0, 0.75)',
      backdropFilter: 'blur(8px)',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      zIndex: 9999,
      padding: '16px'
    }}>
      <div className="glass-card" style={{
        width: '100%',
        maxWidth: '460px',
        maxHeight: '90vh',
        overflowY: 'auto',
        padding: '28px',
        borderRadius: '20px',
        position: 'relative',
        boxShadow: '0 20px 40px rgba(0, 0, 0, 0.5)',
        border: '1px solid rgba(255, 255, 255, 0.15)'
      }}>
        {/* Close button */}
        <button
          type="button"
          onClick={onClose}
          style={{
            position: 'absolute',
            top: '18px',
            right: '18px',
            background: 'var(--bg-input)',
            border: 'none',
            color: 'var(--text-secondary)',
            width: '32px',
            height: '32px',
            borderRadius: '50%',
            cursor: 'pointer',
            fontSize: '18px',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center'
          }}
        >
          ✕
        </button>

        {currentUser ? (
          /* Profile / Already Logged In View */
          <div>
            <div style={{ textAlign: 'center', marginBottom: '24px' }}>
              <div style={{
                width: '64px',
                height: '64px',
                borderRadius: '50%',
                background: 'linear-gradient(135deg, #3b82f6, #06b6d4)',
                margin: '0 auto 12px',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                fontSize: '28px'
              }}>
                👤
              </div>
              <h3 style={{ fontSize: '1.2rem', fontWeight: '800' }}>
                {currentUser.full_name || currentUser.username}
              </h3>
              <p style={{ fontSize: '0.85rem', color: 'var(--text-secondary)' }}>
                {currentUser.email}
              </p>
              <div style={{ marginTop: '8px' }}>
                <span style={{
                  padding: '4px 12px',
                  borderRadius: '12px',
                  fontSize: '0.78rem',
                  fontWeight: '700',
                  background: 'rgba(59, 130, 246, 0.2)',
                  color: '#60a5fa',
                  border: '1px solid rgba(59, 130, 246, 0.3)'
                }}>
                  {currentUser.role === 'admin' ? '👑 ผู้ดูแลระบบ (Admin)' :
                   currentUser.role === 'business_owner' ? '🏢 เจ้าของธุรกิจ (Business Owner)' :
                   '👮 เจ้าหน้าที่เฝ้าระวัง (Operator)'}
                </span>
              </div>
            </div>

            <button
              type="button"
              onClick={async () => {
                await signOut(auth);
                onLogout();
                onClose();
              }}
              className="btn btn-danger"
              style={{ width: '100%', padding: '12px', fontSize: '0.9rem', borderRadius: '10px', fontWeight: '700' }}
            >
              🚪 ออกจากระบบ (Logout)
            </button>
          </div>
        ) : (
          /* Login & Register Tabs */
          <div>
            <div style={{ textAlign: 'center', marginBottom: '20px' }}>
              <div style={{ fontSize: '32px', marginBottom: '8px' }}>🚗</div>
              <h3 style={{ fontSize: '1.25rem', fontWeight: '800' }}>
                เข้าสู่ระบบ KU SRC Traffic
              </h3>
              <p style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>
                เข้าถึงระบบวิเคราะห์ข้อมูลธุรกิจและจัดการกล้อง CCTV
              </p>
            </div>

            {/* Tab switch */}
            <div style={{
              display: 'flex',
              background: 'var(--bg-input)',
              padding: '4px',
              borderRadius: '10px',
              marginBottom: '20px'
            }}>
              <button
                type="button"
                onClick={() => setTab('login')}
                style={{
                  flex: 1,
                  padding: '8px',
                  borderRadius: '8px',
                  border: 'none',
                  cursor: 'pointer',
                  fontWeight: '700',
                  fontSize: '0.85rem',
                  background: tab === 'login' ? 'var(--accent-primary)' : 'transparent',
                  color: tab === 'login' ? '#fff' : 'var(--text-secondary)'
                }}
              >
                เข้าสู่ระบบ (Login)
              </button>
              <button
                type="button"
                onClick={() => setTab('register')}
                style={{
                  flex: 1,
                  padding: '8px',
                  borderRadius: '8px',
                  border: 'none',
                  cursor: 'pointer',
                  fontWeight: '700',
                  fontSize: '0.85rem',
                  background: tab === 'register' ? 'var(--accent-primary)' : 'transparent',
                  color: tab === 'register' ? '#fff' : 'var(--text-secondary)'
                }}
              >
                สมัครสมาชิก (Register)
              </button>
            </div>

            {error && (
              <div style={{
                padding: '10px 14px',
                borderRadius: '8px',
                background: 'rgba(239, 68, 68, 0.15)',
                color: '#ef4444',
                fontSize: '0.82rem',
                marginBottom: '16px',
                border: '1px solid rgba(239, 68, 68, 0.3)'
              }}>
                ⚠️ {error}
              </div>
            )}

            {tab === 'login' ? (
              <form onSubmit={handleLogin} style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
                <div>
                  <label style={{ display: 'block', fontSize: '0.8rem', fontWeight: '700', marginBottom: '6px' }}>
                    ชื่อผู้ใช้ หรือ อีเมล
                  </label>
                  <input
                    type="text"
                    required
                    value={username}
                    onChange={(e) => setUsername(e.target.value)}
                    placeholder="admin หรือ email@example.com"
                    style={{
                      width: '100%',
                      padding: '10px 14px',
                      borderRadius: '8px',
                      border: '1px solid var(--border-color)',
                      background: 'var(--bg-input)',
                      color: 'var(--text-primary)',
                      fontSize: '0.88rem'
                    }}
                  />
                </div>

                <div>
                  <label style={{ display: 'block', fontSize: '0.8rem', fontWeight: '700', marginBottom: '6px' }}>
                    รหัสผ่าน
                  </label>
                  <input
                    type="password"
                    required
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    placeholder="••••••••"
                    style={{
                      width: '100%',
                      padding: '10px 14px',
                      borderRadius: '8px',
                      border: '1px solid var(--border-color)',
                      background: 'var(--bg-input)',
                      color: 'var(--text-primary)',
                      fontSize: '0.88rem'
                    }}
                  />
                </div>

                <button
                  type="submit"
                  disabled={isLoading}
                  className="btn btn-primary"
                  style={{
                    padding: '12px',
                    borderRadius: '10px',
                    fontWeight: '800',
                    fontSize: '0.92rem',
                    marginTop: '8px'
                  }}
                >
                  {isLoading ? 'กำลังเข้าสู่ระบบ...' : '🔐 เข้าสู่ระบบ (Login)'}
                </button>
              </form>
            ) : (
              <form onSubmit={handleRegister} style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
                <div>
                  <label style={{ display: 'block', fontSize: '0.8rem', fontWeight: '700', marginBottom: '6px' }}>
                    ชื่อผู้ใช้ (Username)
                  </label>
                  <input
                    type="text"
                    required
                    value={username}
                    onChange={(e) => setUsername(e.target.value)}
                    placeholder="my_username"
                    style={{
                      width: '100%',
                      padding: '10px 14px',
                      borderRadius: '8px',
                      border: '1px solid var(--border-color)',
                      background: 'var(--bg-input)',
                      color: 'var(--text-primary)',
                      fontSize: '0.88rem'
                    }}
                  />
                </div>

                <div>
                  <label style={{ display: 'block', fontSize: '0.8rem', fontWeight: '700', marginBottom: '6px' }}>
                    ชื่อ-นามสกุล / ชื่อองค์กร
                  </label>
                  <input
                    type="text"
                    value={fullName}
                    onChange={(e) => setFullName(e.target.value)}
                    placeholder="สมชาย ใจดี"
                    style={{
                      width: '100%',
                      padding: '10px 14px',
                      borderRadius: '8px',
                      border: '1px solid var(--border-color)',
                      background: 'var(--bg-input)',
                      color: 'var(--text-primary)',
                      fontSize: '0.88rem'
                    }}
                  />
                </div>

                <div>
                  <label style={{ display: 'block', fontSize: '0.8rem', fontWeight: '700', marginBottom: '6px' }}>
                    อีเมล (Email)
                  </label>
                  <input
                    type="email"
                    required
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    placeholder="contact@company.com"
                    style={{
                      width: '100%',
                      padding: '10px 14px',
                      borderRadius: '8px',
                      border: '1px solid var(--border-color)',
                      background: 'var(--bg-input)',
                      color: 'var(--text-primary)',
                      fontSize: '0.88rem'
                    }}
                  />
                </div>

                <div>
                  <label style={{ display: 'block', fontSize: '0.8rem', fontWeight: '700', marginBottom: '6px' }}>
                    รหัสผ่าน (Password)
                  </label>
                  <input
                    type="password"
                    required
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    placeholder="อย่างน้อย 6 ตัวอักษร"
                    style={{
                      width: '100%',
                      padding: '10px 14px',
                      borderRadius: '8px',
                      border: '1px solid var(--border-color)',
                      background: 'var(--bg-input)',
                      color: 'var(--text-primary)',
                      fontSize: '0.88rem'
                    }}
                  />
                </div>

                <div>
                  <label style={{ display: 'block', fontSize: '0.8rem', fontWeight: '700', marginBottom: '6px' }}>
                    ประเภทบทบาท (Role)
                  </label>
                  <select
                    value={role}
                    onChange={(e) => setRole(e.target.value)}
                    style={{
                      width: '100%',
                      padding: '10px 14px',
                      borderRadius: '8px',
                      border: '1px solid var(--border-color)',
                      background: 'var(--bg-input)',
                      color: 'var(--text-primary)',
                      fontSize: '0.88rem'
                    }}
                  >
                    <option value="business_owner">🏢 เจ้าของธุรกิจ / ผู้จัดการสาขา (Business Owner)</option>
                    <option value="operator">👮 เจ้าหน้าที่เฝ้าระวังความปลอดภัย (Operator)</option>
                    <option value="admin">👑 ผู้ดูแลระบบ (Admin)</option>
                  </select>
                </div>

                <button
                  type="submit"
                  disabled={isLoading}
                  className="btn btn-primary"
                  style={{
                    padding: '12px',
                    borderRadius: '10px',
                    fontWeight: '800',
                    fontSize: '0.92rem',
                    marginTop: '8px'
                  }}
                >
                  {isLoading ? 'กำลังลงทะเบียน...' : '✨ สมัครสมาชิก (Register)'}
                </button>
              </form>
            )}

            {/* Quick Demo Login Buttons */}
            {demoAccounts.length > 0 && (
              <div style={{ marginTop: '24px', paddingTop: '16px', borderTop: '1px solid var(--border-color)' }}>
                <div style={{ fontSize: '0.75rem', fontWeight: '700', color: 'var(--text-secondary)', marginBottom: '10px' }}>
                  ⚡ เข้าสู่ระบบแบบด่วน (One-Click Demo Login):
                </div>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                  {demoAccounts.map((acc) => (
                    <button
                      key={acc.username}
                      type="button"
                      onClick={() => handleQuickDemoLogin(acc)}
                      style={{
                        padding: '8px 12px',
                        borderRadius: '8px',
                        border: '1px solid var(--border-color)',
                        background: 'var(--bg-input)',
                        color: 'var(--text-primary)',
                        cursor: 'pointer',
                        fontSize: '0.78rem',
                        fontWeight: '600',
                        textAlign: 'left',
                        display: 'flex',
                        justifyContent: 'space-between',
                        alignItems: 'center',
                        transition: 'all 0.15s ease'
                      }}
                    >
                      <span>{acc.label}</span>
                      <span style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>คลิกเพื่อเข้าทันที →</span>
                    </button>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
