/**
 * Multi-Tab Authentication Synchronization & Session Boundary Guard
 * 
 * Synchronizes login, logout, and account transitions across all open browser tabs
 * using BroadcastChannel and storage events. Binds state, drafts, and requests to
 * (userId, sessionGeneration) to prevent cross-account overwrites and race conditions.
 */

export interface AuthSession {
  token: string | null;
  user: any | null;
  sessionGeneration: string | null;
}

export type AuthSyncEventType = 
  | 'LOGIN'
  | 'LOGOUT'
  | 'ACCOUNT_SWITCH'
  | 'SESSION_INVALIDATED';

export interface AuthSyncEvent {
  type: AuthSyncEventType;
  userId?: string | null;
  sessionGeneration?: string | null;
  user?: any | null;
  timestamp: number;
}

const TOKEN_KEY = 'intervyn_token';
const USER_KEY = 'intervyn_user';
const SESSION_GEN_KEY = 'intervyn_session_gen';
const CHANNEL_NAME = 'intervyn_auth_sync_v1';

let broadcastChannel: BroadcastChannel | null = null;
try {
  if (typeof window !== 'undefined' && 'BroadcastChannel' in window) {
    broadcastChannel = new BroadcastChannel(CHANNEL_NAME);
  }
} catch (e) {
  console.warn('BroadcastChannel not supported in this environment, falling back to storage events');
}

const listeners = new Set<(event: AuthSyncEvent) => void>();

function notifyListeners(event: AuthSyncEvent) {
  listeners.forEach(fn => {
    try {
      fn(event);
    } catch (err) {
      console.error('Error in auth sync listener:', err);
    }
  });
}

// Listen to incoming BroadcastChannel messages
if (broadcastChannel) {
  broadcastChannel.onmessage = (msg: MessageEvent<AuthSyncEvent>) => {
    if (msg && msg.data) {
      notifyListeners(msg.data);
    }
  };
}

// Fallback & redundancy: listen to storage events
if (typeof window !== 'undefined') {
  window.addEventListener('storage', (e: StorageEvent) => {
    if (e.key === TOKEN_KEY || e.key === USER_KEY || e.key === SESSION_GEN_KEY) {
      const current = getAuthSession();
      if (!current.token) {
        notifyListeners({
          type: 'LOGOUT',
          timestamp: Date.now()
        });
      } else {
        notifyListeners({
          type: 'ACCOUNT_SWITCH',
          userId: current.user?.id,
          sessionGeneration: current.sessionGeneration,
          user: current.user,
          timestamp: Date.now()
        });
      }
    }
  });

  // Background tab resumption check: check if storage changed while tab was inactive
  let lastObservedUserId: string | null = null;
  let lastObservedSessionGen: string | null = null;

  try {
    const s = getAuthSession();
    lastObservedUserId = s.user?.id || null;
    lastObservedSessionGen = s.sessionGeneration || null;
  } catch {}

  document.addEventListener('visibilitychange', () => {
    if (document.visibilityState === 'visible') {
      const latest = getAuthSession();
      const currentUid = latest.user?.id || null;
      const currentGen = latest.sessionGeneration || null;

      if (currentUid !== lastObservedUserId || currentGen !== lastObservedSessionGen) {
        lastObservedUserId = currentUid;
        lastObservedSessionGen = currentGen;
        notifyListeners({
          type: latest.token ? 'ACCOUNT_SWITCH' : 'LOGOUT',
          userId: currentUid,
          sessionGeneration: currentGen,
          user: latest.user,
          timestamp: Date.now()
        });
      }
    }
  });
}

export function getAuthSession(): AuthSession {
  if (typeof window === 'undefined') {
    return { token: null, user: null, sessionGeneration: null };
  }

  try {
    const token = localStorage.getItem(TOKEN_KEY) || null;
    const userStr = localStorage.getItem(USER_KEY);
    const user = userStr ? JSON.parse(userStr) : null;
    let sessionGen = localStorage.getItem(SESSION_GEN_KEY) || null;

    // If sessionGen is missing from storage but user has it, recover it
    if (!sessionGen && user?.session_generation) {
      sessionGen = user.session_generation;
      localStorage.setItem(SESSION_GEN_KEY, sessionGen);
    }

    return { token, user, sessionGeneration: sessionGen };
  } catch {
    return { token: null, user: null, sessionGeneration: null };
  }
}

export function setAuthSession(token: string, user: any, sessionGeneration?: string) {
  if (typeof window === 'undefined') return;

  const sessionGen = sessionGeneration || user?.session_generation || `sess_${Date.now()}_${Math.random().toString(36).substring(2, 9)}`;
  const cleanUser = {
    ...user,
    session_generation: sessionGen
  };

  try {
    localStorage.setItem(TOKEN_KEY, token);
    localStorage.setItem(USER_KEY, JSON.stringify(cleanUser));
    localStorage.setItem(SESSION_GEN_KEY, sessionGen);
  } catch (err) {
    console.error('Failed to store auth session:', err);
  }

  const event: AuthSyncEvent = {
    type: 'LOGIN',
    userId: cleanUser.id,
    sessionGeneration: sessionGen,
    user: cleanUser,
    timestamp: Date.now()
  };

  if (broadcastChannel) {
    try {
      broadcastChannel.postMessage(event);
    } catch {}
  }
  notifyListeners(event);
}

export function clearAuthSession(broadcast: boolean = true) {
  if (typeof window === 'undefined') return;

  try {
    localStorage.removeItem(TOKEN_KEY);
    localStorage.removeItem(USER_KEY);
    localStorage.removeItem(SESSION_GEN_KEY);
  } catch (err) {
    console.error('Failed to clear auth session:', err);
  }

  if (broadcast) {
    const event: AuthSyncEvent = {
      type: 'LOGOUT',
      timestamp: Date.now()
    };
    if (broadcastChannel) {
      try {
        broadcastChannel.postMessage(event);
      } catch {}
    }
    notifyListeners(event);
  }
}

export function subscribeAuthSync(listener: (event: AuthSyncEvent) => void): () => void {
  listeners.add(listener);
  return () => {
    listeners.delete(listener);
  };
}

export function getAuthSessionHeaders(): Record<string, string> {
  const session = getAuthSession();
  const headers: Record<string, string> = {};

  if (session.token) {
    headers['Authorization'] = `Bearer ${session.token}`;
  }
  if (session.user?.id) {
    headers['X-Expected-User-Id'] = String(session.user.id);
  }
  if (session.sessionGeneration) {
    headers['X-Session-Generation'] = String(session.sessionGeneration);
  }

  return headers;
}
