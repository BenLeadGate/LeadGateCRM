// Gemeinsame Auth-Funktionen

const API_BASE = '/api';

// Token-Management
function getToken() {
    return localStorage.getItem('access_token');
}

function saveToken(token) {
    localStorage.setItem('access_token', token);
}

function removeToken() {
    localStorage.removeItem('access_token');
}

// Prüft ob User eingeloggt ist und leitet bei Bedarf zur Login-Seite weiter
async function checkAuth() {
    // Verhindere Endlosschleife wenn bereits auf Login-Seite
    if (window.location.pathname === '/login.html' || window.location.pathname === '/') {
        return true; // Erlaube Zugriff auf Login-Seite
    }
    
    const token = getToken();
    if (!token) {
        window.location.href = '/login.html';
        return false;
    }
    
    // Token validieren mit Timeout
    try {
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), 5000); // 5 Sekunden Timeout
        
        const response = await fetch(`${API_BASE}/auth/me`, {
            headers: {
                'Authorization': `Bearer ${token}`
            },
            signal: controller.signal
        });
        
        clearTimeout(timeoutId);
        
        if (!response.ok) {
            removeToken();
            window.location.href = '/login.html';
            return false;
        }
        return true;
    } catch (error) {
        // Bei Timeout oder Netzwerkfehler: Token entfernen und zur Login-Seite
        removeToken();
        if (error.name !== 'AbortError') {
            console.error('Auth-Fehler:', error);
        }
        window.location.href = '/login.html';
        return false;
    }
}

// Wrapper für fetch mit automatischem Token
async function authFetch(url, options = {}) {
    const token = getToken();
    
    const headers = {
        ...options.headers,
    };
    
    if (token) {
        headers['Authorization'] = `Bearer ${token}`;
    }
    
    const response = await fetch(url, {
        ...options,
        headers
    });
    
    // Bei 401 zur Login-Seite weiterleiten
    if (response.status === 401) {
        removeToken();
        window.location.href = '/login.html';
        return response;
    }
    
    return response;
}

// Logout-Funktion
function logout() {
    removeToken();
    window.location.href = '/login.html';
}

