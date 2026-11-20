// Track page view
function trackPageView() {
    var page = window.location.pathname;
    var projectId = getProjectId();
    var eventName = 'page_view';
    if (page === '/discover') eventName = 'discover_view';
    if (projectId) eventName = 'project_view';
    trackEvent(eventName, projectId);
}

function trackEvent(eventName, projectId) {
    // Strict validation - never send invalid events. The allowlist is
    // generated from backend/app/routes_analytics.py VALID_EVENTS so the two
    // sides cannot drift; see static/analytics_events.js.
    var VALID_EVENTS = window.CRITIQUE_VALID_ANALYTICS_EVENTS || [];
    if (!eventName || VALID_EVENTS.indexOf(eventName) === -1) {
        return; // Silently skip invalid events
    }
    var url = '/api/analytics/track?event_name=' + encodeURIComponent(eventName);
    if (projectId && !isNaN(projectId)) {
        url += '&project_id=' + parseInt(projectId);
    }
    // keepalive lets the request outlive a click that navigates away (the
    // GitHub sign-in link), so paired click events are not cancelled
    // independently by the browser and lost.
    fetch(url, { method: 'POST', credentials: 'same-origin', keepalive: true }).catch(function() {});
}

function getProjectId() {
    var match = window.location.pathname.match(/^\/project\/(\d+)\/?$/);
    return match ? parseInt(match[1]) : null;
}

window.CritiqueAnalytics = {
    trackEvent: trackEvent,
    getProjectId: getProjectId,
    trackPageView: trackPageView
};
