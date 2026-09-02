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
            container.setAttribute('aria-live', 'polite');
            document.body.appendChild(container);
        }

        var toast = document.createElement('div');
        toast.className = 'toast toast-' + type;
        toast.setAttribute('role', 'status');

        var icon = document.createElement('span');
        icon.className = 'toast-icon';
        icon.setAttribute('aria-hidden', 'true');
        icon.textContent = type === 'success' ? '✓' : type === 'error' ? '✕' : 'ℹ';

        var text = document.createElement('span');
        text.className = 'toast-text';
        text.textContent = message;

        toast.appendChild(icon);
        toast.appendChild(text);

        container.appendChild(toast);

        // Auto dismiss after 3.5 seconds
        setTimeout(function() {
            toast.classList.add('toast-hide');
            setTimeout(function() {
                if (toast.parentNode) toast.parentNode.removeChild(toast);
            }, 200);
        }, 3500);

        // Click to dismiss
        toast.addEventListener('click', function() {
            toast.classList.add('toast-hide');
            setTimeout(function() {
                if (toast.parentNode) toast.parentNode.removeChild(toast);
            }, 200);
        });
    }

    // ============ MODAL SYSTEM ============
    function showConfirmModal(options) {
        var title = options.title || 'Confirm';
        var message = options.message || '';
        var confirmText = options.confirmText || 'Confirm';
        var cancelText = options.cancelText || 'Cancel';
        var destructive = options.destructive !== false;
        var onConfirm = options.onConfirm || function() {};

        // Create backdrop
        var backdrop = document.createElement('div');
        backdrop.className = 'modal-backdrop';
        backdrop.setAttribute('data-modal-backdrop', '');

        // Create modal
        var modal = document.createElement('div');
        modal.className = 'modal';
        modal.setAttribute('role', 'dialog');
        modal.setAttribute('aria-modal', 'true');
        modal.setAttribute('aria-labelledby', 'modal-title');

        var titleEl = document.createElement('h3');
        titleEl.id = 'modal-title';
        titleEl.className = 'modal-title';
        titleEl.textContent = title;

        var bodyEl = document.createElement('div');
        bodyEl.className = 'modal-body';
        bodyEl.textContent = message;

        var actionsEl = document.createElement('div');
        actionsEl.className = 'modal-actions';

        var cancelBtn = document.createElement('button');
        cancelBtn.className = 'btn btn-secondary';
        cancelBtn.textContent = cancelText;
        cancelBtn.setAttribute('type', 'button');

        var confirmBtn = document.createElement('button');
        confirmBtn.className = destructive ? 'btn btn-danger' : 'btn btn-primary';
        confirmBtn.textContent = confirmText;
        confirmBtn.setAttribute('type', 'button');

        actionsEl.appendChild(cancelBtn);
        actionsEl.appendChild(confirmBtn);

        modal.appendChild(titleEl);
        modal.appendChild(bodyEl);
        modal.appendChild(actionsEl);

        backdrop.appendChild(modal);
        document.body.appendChild(backdrop);

        // Prevent body scroll
        document.body.style.overflow = 'hidden';

        function closeModal() {
            document.body.style.overflow = '';
            if (backdrop.parentNode) backdrop.parentNode.removeChild(backdrop);
        }

        function handleConfirm() {
            confirmBtn.disabled = true;
            confirmBtn.textContent = 'Working...';
            onConfirm(function() {
                closeModal();
            }, function() {
                confirmBtn.disabled = false;
                confirmBtn.textContent = confirmText;
            });
        }

        cancelBtn.addEventListener('click', closeModal);
        backdrop.addEventListener('click', function(e) {
            if (e.target === backdrop) closeModal();
        });
        confirmBtn.addEventListener('click', handleConfirm);

        // Escape key
        document.addEventListener('keydown', function escHandler(e) {
            if (e.key === 'Escape') {
                closeModal();
                document.removeEventListener('keydown', escHandler);
            }
        });

        // Focus confirm button
        setTimeout(function() { confirmBtn.focus(); }, 100);

        return {
            close: closeModal
        };
    }

    return {
        showToast: showToast,
        showConfirmModal: showConfirmModal
    };
})();
