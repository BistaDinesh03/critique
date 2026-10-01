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
    // Strict validation - never send invalid events
    var VALID_EVENTS = [
        'page_view',
        'discover_view',
        'project_view',
        'feedback_start',
        'feedback_submit',
        'project_submit',
        'login_prompt_shown',
        'login_started',
        'login_success',
        'feedback_resume',
        'feedback_submit_attempt',
        'feedback_submit_error',
        'auth_method_selected_github',
        'auth_method_selected_email',
        'email_verification_sent',
        'email_verification_success',
        'share_ui_shown',
        'share_copy_link',
        'share_copy_post',
        'share_option_clicked'
    ];
    if (!eventName || VALID_EVENTS.indexOf(eventName) === -1) {
        return; // Silently skip invalid events
    }
    var url = '/api/analytics/track?event_name=' + encodeURIComponent(eventName);
    if (projectId && !isNaN(projectId)) {
        url += '&project_id=' + parseInt(projectId);
    }
    fetch(url, { method: 'POST', credentials: 'same-origin' }).catch(function() {});
}

function getProjectId() {
    var match = window.location.pathname.match(/\/project\/(\d+)/);
    return match ? parseInt(match[1]) : null;
}

window.CritiqueAnalytics = {
    trackEvent: trackEvent,
    getProjectId: getProjectId,
    trackPageView: trackPageView
};
