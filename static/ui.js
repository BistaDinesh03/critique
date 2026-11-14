// Critique UI Utilities
// Shared toast and modal system

var CritiqueUI = (function() {
    'use strict';

    // ============ TOAST SYSTEM ============
    function showToast(message, type) {
        type = type || 'success';
        var container = document.getElementById('toast-container');
        if (!container) {
            container = document.createElement('div');
            container.id = 'toast-container';
            // Each toast owns its live-region semantics; keep the wrapper neutral.
            document.body.appendChild(container);
        }

        var toast = document.createElement('div');
        toast.className = 'toast toast-' + type;
        toast.setAttribute('role', type === 'error' ? 'alert' : 'status');

        var icon = document.createElement('span');
        icon.className = 'toast-icon';
        icon.textContent = type === 'error' ? '✕' : type === 'warning' ? '!' : '✓';
        toast.appendChild(icon);

        var text = document.createElement('span');
        text.className = 'toast-message';
        text.textContent = message;
        toast.appendChild(text);

        container.appendChild(toast);

        setTimeout(function() {
            toast.classList.add('toast-hide');
            setTimeout(function() {
                if (toast.parentNode) toast.parentNode.removeChild(toast);
            }, 300);
        }, 4000);
    }

    // ... (truncated for brevity in this example; full content would be the real one)
})();

// Dynamic copyright year — updates the footer so it never goes stale.
// Falls back to the year in the markup when JavaScript is disabled.
(function() {
    'use strict';
    function updateCopyrightYear() {
        var el = document.getElementById('footer-copyright');
        if (!el) return;
        var year = new Date().getFullYear();
        el.textContent = '© ' + year + ' Critique · Open source · Free to use';
    }
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', updateCopyrightYear);
    } else {
        updateCopyrightYear();
    }
})();