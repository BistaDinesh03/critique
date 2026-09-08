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
    var url = '/api/analytics/track?event_name=' + eventName;
    if (projectId) url += '&project_id=' + projectId;
    fetch(url, { method: 'POST', credentials: 'same-origin' }).catch(function() {});
}

function getProjectId() {
    var match = window.location.pathname.match(/\/project\/(\d+)/);
    return match ? parseInt(match[1]) : null;
}

// Expose for page-specific use
window.CritiqueAnalytics = {
    trackEvent: trackEvent,
    getProjectId: getProjectId,
    trackPageView: trackPageView
};
