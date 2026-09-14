// Sanketak dashboard backend settings.
// Filename kept as supabase-config.js because every page loads it by that
// name and the HTML is not ours to change. The contents are no longer
// Supabase — this is the FastAPI backend configuration.

window.SanketakConfig = {
    // Base URL of the FastAPI backend. No trailing slash.
    apiBaseUrl: "http://localhost:8000",

    // localStorage keys, in one place so nothing hardcodes a string.
    tokenKey: "sanketak_access_token",
    emailKey: "sanketak_email",

    // Where to send a visitor whose token is missing or rejected.
    loginPage: "login.html",
    dashboardPage: "dash.html"
};

// Token helper. Shared by login.js, hse-services.js and hse-app.js.
window.SanketakAuth = {
    getToken: function () {
        try {
            return localStorage.getItem(window.SanketakConfig.tokenKey) || "";
        } catch (error) {
            return "";
        }
    },

    setToken: function (token) {
        try {
            localStorage.setItem(window.SanketakConfig.tokenKey, token);
        } catch (error) {
            // Private browsing or blocked storage. The session simply will
            // not persist; the caller still has the token for this page.
        }
    },

    clearToken: function () {
        try {
            localStorage.removeItem(window.SanketakConfig.tokenKey);
        } catch (error) {
            // Nothing to clear.
        }
    },

    isSignedIn: function () {
        return Boolean(window.SanketakAuth.getToken());
    },

    // Authorization header for every authenticated request, or {} when
    // there is no token so the caller still gets a well-formed 401.
    authHeaders: function () {
        const token = window.SanketakAuth.getToken();
        return token ? { Authorization: "Bearer " + token } : {};
    },

    apiUrl: function (path) {
        return window.SanketakConfig.apiBaseUrl + path;
    }
};
