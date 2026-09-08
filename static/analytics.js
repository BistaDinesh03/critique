// Track page view
function trackPageView() {
    var page = window.location.pathname;
    fetch('/api/analytics/track?event_name=page_view&project_id=' + getProjectId(), {
        method: 'POST',
        credentials: 'same-origin'
    }).catch(function() {});
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
