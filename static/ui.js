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

    // ============ AUTH CHOICE (GitHub + email) ============
    // One shared "Continue with GitHub / Continue with email" prompt so every
    // login-required action offers both existing methods the same way.

    var GITHUB_ICON = '<svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M15 22v-4a4.8 4.8 0 0 0-1-3.5c3 0 6-2 6-5.5.08-1.25-.27-2.48-1-3.5.28-1.15.28-2.35 0-3.5 0 0-1 0-3 1.5-2.64-.5-5.36-.5-8 0C6 2 5 2 5 2c-.3 1.15-.3 2.35 0 3.5A5.403 5.403 0 0 0 4 9c0 3.5 3 5.5 6 5.5-.39.49-.68 1.05-.85 1.65-.17.6-.22 1.23-.15 1.85v4"/><path d="M9 18c-4.51 2-5-2-7-2"/></svg>';
    var EMAIL_ICON = '<svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><rect x="2" y="4" width="20" height="16" rx="2"/><path d="m22 7-10 7L2 7"/></svg>';

    function trackAuthEvent(name, projectId) {
        if (window.CritiqueAnalytics && typeof window.CritiqueAnalytics.trackEvent === 'function') {
            window.CritiqueAnalytics.trackEvent(name, projectId);
        }
    }

    function readCsrfToken() {
        if (typeof window.getCsrfToken === 'function') {
            try {
                var fromPage = window.getCsrfToken();
                if (fromPage) return fromPage;
            } catch (e) {}
        }
        var match = document.cookie.match(/(?:^|;\s*)critique_csrf=([^;]+)/);
        return match ? decodeURIComponent(match[1]) : '';
    }

    function authReturnTo(config) {
        return (config && config.returnTo) || window.location.pathname;
    }

    function appendText(el, className, text) {
        var node = document.createElement('p');
        node.className = className;
        node.textContent = text;
        el.appendChild(node);
        return node;
    }

    // Shared copy. Every login gate uses the same words for the same action so
    // the choice feels like one product rather than a per-page form.
    var AUTH_COPY = {
        welcomeTitle: 'Welcome to Critique',
        welcomeMessage: 'Get honest feedback on your projects from real people.',
        githubNote: 'GitHub takes one click if you already have an account. Email works just as well.',
        emailTitle: 'Continue with email',
        emailMessage: "We'll send you a secure sign-in link. No password needed.",
        send: 'Email me a sign-in link',
        sending: 'Sending sign-in link\u2026',
        checkTitle: 'Check your inbox',
        resend: 'Resend sign-in link',
        resending: 'Sending another link\u2026',
        changeEmail: 'Change email',
        genericError: "We couldn't send the link. Check your connection and try again.",
        rateLimitError: 'Too many attempts. Please wait a minute, then try again.'
    };

    var EMAIL_PATTERN = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    var RESEND_COOLDOWN_MS = 60 * 1000;
    var emailFieldSeq = 0;

    function makeTitle(text) {
        var title = document.createElement('h2');
        title.className = 'login-prompt-title';
        title.textContent = text;
        title.setAttribute('tabindex', '-1');
        return title;
    }

    function focusAfterRender(node) {
        if (!node || typeof node.focus !== 'function') return;
        try {
            node.focus({ preventScroll: true });
        } catch (e) {
            try { node.focus(); } catch (e2) {}
        }
    }

    // Renders: title / message / GitHub button / email button / supporting notes.
    // config = {
    //   title, message, notes[], returnTo, context,
    //   onStart(method)  -> called when a method is chosen (save drafts here),
    //   emailSentHint, resendCooldownMs
    // }
    function renderAuthChoice(el, config, focusTarget) {
        if (!el) return;
        config = config || {};
        var context = config.context === undefined ? null : config.context;

        el.innerHTML = '';
        el.className = 'login-prompt';
        el.removeAttribute('aria-busy');

        var title = makeTitle(config.title || AUTH_COPY.welcomeTitle);
        el.appendChild(title);
        appendText(el, 'login-prompt-text', config.message || AUTH_COPY.welcomeMessage);

        var actions = document.createElement('div');
        actions.className = 'login-prompt-actions';

        var ghLink = document.createElement('a');
        ghLink.className = 'btn btn-primary';
        ghLink.href = '/auth/login?return_to=' + encodeURIComponent(authReturnTo(config));
        ghLink.innerHTML = GITHUB_ICON + '<span>Continue with GitHub</span>';
        ghLink.addEventListener('click', function() {
            trackAuthEvent('auth_method_selected_github', context);
            if (typeof config.onStart === 'function') config.onStart('github');
            trackAuthEvent('login_started', context);
        });
        actions.appendChild(ghLink);

        var emailBtn = document.createElement('button');
        emailBtn.type = 'button';
        emailBtn.className = 'btn btn-secondary';
        emailBtn.innerHTML = EMAIL_ICON + '<span>Continue with email</span>';
        emailBtn.addEventListener('click', function() {
            trackAuthEvent('auth_method_selected_email', context);
            if (typeof config.onStart === 'function') config.onStart('email');
            renderEmailForm(el, config);
        });
        actions.appendChild(emailBtn);

        el.appendChild(actions);

        var notes = config.notes && config.notes.length ? config.notes.slice() : ['No password required.'];
        if (notes.indexOf(AUTH_COPY.githubNote) === -1) notes.push(AUTH_COPY.githubNote);
        for (var i = 0; i < notes.length; i++) {
            appendText(el, 'login-prompt-note', notes[i]);
        }

        // Focus management: the gate is a new screen, so keyboard users start
        // at its heading. Going Back from the email form targets the email
        // option they came from instead.
        if (focusTarget === 'email') focusAfterRender(emailBtn);
        else focusAfterRender(title);
    }

    function renderEmailForm(el, config, initialEmail) {
        config = config || {};
        var context = config.context === undefined ? null : config.context;

        el.innerHTML = '';
        el.className = 'login-prompt';
        el.removeAttribute('aria-busy');

        el.appendChild(makeTitle(AUTH_COPY.emailTitle));
        appendText(el, 'login-prompt-text', AUTH_COPY.emailMessage);

        var form = document.createElement('form');
        form.className = 'login-prompt-form';
        form.setAttribute('novalidate', 'novalidate');

        var fieldId = 'auth-email-' + (++emailFieldSeq);
        var errorId = fieldId + '-error';

        var field = document.createElement('div');
        field.className = 'login-prompt-field';

        var label = document.createElement('label');
        label.className = 'login-prompt-field-label';
        label.setAttribute('for', fieldId);
        label.textContent = 'Email';
        field.appendChild(label);

        var emailInput = document.createElement('input');
        emailInput.type = 'email';
        emailInput.id = fieldId;
        emailInput.name = 'email';
        emailInput.required = true;
        emailInput.autocomplete = 'email';
        emailInput.placeholder = 'you@example.com';
        emailInput.value = initialEmail || '';
        emailInput.setAttribute('autocomplete', 'email');
        emailInput.setAttribute('inputmode', 'email');
        emailInput.setAttribute('autocapitalize', 'none');
        emailInput.setAttribute('spellcheck', 'false');
        emailInput.setAttribute('aria-describedby', errorId);
        emailInput.setAttribute('aria-invalid', 'false');
        emailInput.className = 'form-input';
        field.appendChild(emailInput);

        var errorEl = document.createElement('p');
        errorEl.className = 'login-prompt-error';
        errorEl.id = errorId;
        errorEl.setAttribute('role', 'alert');
        field.appendChild(errorEl);

        form.appendChild(field);

        var sendBtn = document.createElement('button');
        sendBtn.type = 'submit';
        sendBtn.className = 'btn btn-primary';
        sendBtn.textContent = AUTH_COPY.send;
        form.appendChild(sendBtn);

        var backBtn = document.createElement('button');
        backBtn.type = 'button';
        backBtn.className = 'btn-link';
        backBtn.textContent = 'Back';
        backBtn.setAttribute('aria-label', 'Back to sign-in options');
        backBtn.addEventListener('click', function() {
            if (submitting) return;
            renderAuthChoice(el, config, 'email');
        });
        form.appendChild(backBtn);

        var submitting = false;

        function setBusy(busy) {
            submitting = busy;
            sendBtn.disabled = busy;
            backBtn.disabled = busy;
            sendBtn.setAttribute('aria-busy', busy ? 'true' : 'false');
            sendBtn.textContent = busy ? AUTH_COPY.sending : AUTH_COPY.send;
        }

        function showError(message) {
            errorEl.textContent = message;
            emailInput.setAttribute('aria-invalid', 'true');
        }

        emailInput.addEventListener('input', function() {
            if (!errorEl.textContent) return;
            errorEl.textContent = '';
            emailInput.setAttribute('aria-invalid', 'false');
        });

        form.addEventListener('submit', async function(e) {
            e.preventDefault();
            // A second submit while the first request is in flight must not
            // send a second link.
            if (submitting) return;
            errorEl.textContent = '';
            emailInput.setAttribute('aria-invalid', 'false');

            var emailValue = (emailInput.value || '').trim();
            if (!EMAIL_PATTERN.test(emailValue)) {
                showError('Enter a valid email address, like you@example.com.');
                focusAfterRender(emailInput);
                return;
            }

            setBusy(true);

            try {
                var response = await fetch('/auth/email/start', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-CSRF-Token': readCsrfToken()
                    },
                    credentials: 'same-origin',
                    body: JSON.stringify({
                        email: emailValue,
                        return_to: authReturnTo(config)
                    })
                });
                if (response.ok) {
                    trackAuthEvent('email_verification_sent', context);
                    // Success is only shown after the backend confirmed the
                    // request; the endpoint always answers generically, so this
                    // never reveals whether an account exists.
                    renderCheckEmail(el, config, emailValue);
                    return;
                }
                setBusy(false);
                showError(response.status === 429
                    ? AUTH_COPY.rateLimitError
                    : AUTH_COPY.genericError);
            } catch (err) {
                setBusy(false);
                showError(AUTH_COPY.genericError);
            }
        });

        el.appendChild(form);
        focusAfterRender(emailInput);
    }

    function renderCheckEmail(el, config, emailValue) {
        config = config || {};
        var context = config.context === undefined ? null : config.context;
        var cooldownMs = typeof config.resendCooldownMs === 'number'
            ? config.resendCooldownMs
            : RESEND_COOLDOWN_MS;

        el.innerHTML = '';
        el.className = 'login-prompt';
        el.removeAttribute('aria-busy');

        var title = makeTitle(AUTH_COPY.checkTitle);
        el.appendChild(title);

        var sent = document.createElement('p');
        sent.className = 'login-prompt-text';
        sent.appendChild(document.createTextNode('We sent a secure sign-in link to '));
        var address = document.createElement('strong');
        address.className = 'login-prompt-email';
        address.textContent = emailValue;
        sent.appendChild(address);
        sent.appendChild(document.createTextNode('.'));
        el.appendChild(sent);

        appendText(
            el,
            'login-prompt-note',
            config.emailSentHint || 'Click the link in the email to finish signing in.'
        );
        appendText(
            el,
            'login-prompt-note',
            'The link expires in 15 minutes and can only be used once.'
        );
        appendText(
            el,
            'login-prompt-note',
            "Don't see it? Check your spam or promotions folder."
        );

        var status = document.createElement('p');
        status.className = 'login-prompt-status';
        status.setAttribute('role', 'status');
        status.setAttribute('aria-live', 'polite');
        el.appendChild(status);

        var resendBtn = document.createElement('button');
        resendBtn.type = 'button';
        resendBtn.className = 'btn btn-secondary';
        resendBtn.textContent = AUTH_COPY.resend;
        el.appendChild(resendBtn);

        var changeBtn = document.createElement('button');
        changeBtn.type = 'button';
        changeBtn.className = 'btn-link';
        changeBtn.textContent = AUTH_COPY.changeEmail;
        el.appendChild(changeBtn);

        if (cooldownMs <= 0) {
            resendBtn.disabled = false;
        }

        var lastSentAt = Date.now();
        var resending = false;
        var timer = null;

        function secondsLeft() {
            var elapsed = Date.now() - lastSentAt;
            var left = cooldownMs - elapsed;
            return left > 0 ? Math.ceil(left / 1000) : 0;
        }

        function paintCooldown() {
            var left = secondsLeft();
            if (left > 0) {
                resendBtn.disabled = true;
                resendBtn.textContent = 'Resend in ' + left + 's';
            } else {
                resendBtn.disabled = false;
                resendBtn.textContent = AUTH_COPY.resend;
            }
        }

        paintCooldown();
        if (cooldownMs > 0 && typeof setInterval === 'function') {
            timer = setInterval(function() {
                paintCooldown();
                if (secondsLeft() === 0 && timer !== null) {
                    clearInterval(timer);
                    timer = null;
                }
            }, 1000);
        }

        resendBtn.addEventListener('click', async function() {
            if (resending) return;
            var left = secondsLeft();
            if (left > 0) {
                status.textContent = 'You can request another link in ' + left + ' seconds.';
                return;
            }

            resending = true;
            status.textContent = '';
            resendBtn.disabled = true;
            resendBtn.setAttribute('aria-busy', 'true');
            resendBtn.textContent = AUTH_COPY.resending;

            try {
                var response = await fetch('/auth/email/start', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-CSRF-Token': readCsrfToken()
                    },
                    credentials: 'same-origin',
                    body: JSON.stringify({
                        email: emailValue,
                        return_to: authReturnTo(config)
                    })
                });
                if (response.ok) {
                    lastSentAt = Date.now();
                    status.textContent = 'A new sign-in link is on its way. Check your inbox.';
                    paintCooldown();
                } else if (response.status === 429) {
                    status.textContent = AUTH_COPY.rateLimitError;
                    resendBtn.disabled = false;
                    resendBtn.textContent = AUTH_COPY.resend;
                } else {
                    status.textContent = AUTH_COPY.genericError;
                    resendBtn.disabled = false;
                    resendBtn.textContent = AUTH_COPY.resend;
                }
            } catch (err) {
                status.textContent = AUTH_COPY.genericError;
                resendBtn.disabled = false;
                resendBtn.textContent = AUTH_COPY.resend;
            }

            resending = false;
            resendBtn.setAttribute('aria-busy', 'false');
        });

        changeBtn.addEventListener('click', function() {
            if (resending) return;
            if (timer !== null) {
                clearInterval(timer);
                timer = null;
            }
            renderEmailForm(el, config, emailValue);
        });

        focusAfterRender(title);
    }

    // Adds an auth-choice menu to the navbar Login button. The button keeps its
    // href, so with JavaScript unavailable it still starts a GitHub login.
    var navLoginPromptShown = false;

    function initNavLogin() {
        var btn = document.getElementById('login-btn');
        var nav = document.getElementById('navbar-nav');
        if (!btn || !nav || !btn.parentNode || btn.dataset.authMenuInit === 'true') return;
        btn.dataset.authMenuInit = 'true';

        btn.setAttribute('aria-haspopup', 'true');
        btn.setAttribute('aria-expanded', 'false');
        btn.setAttribute('aria-controls', 'nav-login-menu');
        // The markup still labels this control "Login with GitHub", which was
        // true while the link went straight to GitHub. It now opens a choice of
        // both methods, so the accessible name follows the visible "Login" text.
        btn.setAttribute('aria-label', 'Login');

        var menu = document.createElement('div');
        menu.className = 'nav-login-menu';
        menu.id = 'nav-login-menu';
        menu.hidden = true;

        var panel = document.createElement('div');
        menu.appendChild(panel);
        btn.parentNode.insertBefore(menu, btn.nextSibling);

        function closeMenu() {
            if (menu.hidden) return;
            menu.hidden = true;
            btn.setAttribute('aria-expanded', 'false');
        }

        function openMenu() {
            menu.hidden = false;
            btn.setAttribute('aria-expanded', 'true');
            if (!navLoginPromptShown) {
                navLoginPromptShown = true;
                trackAuthEvent('login_prompt_shown', null);
            }
            renderAuthChoice(panel, {
                returnTo: window.location.pathname + window.location.search,
                emailSentHint: 'Click the link in the email to finish signing in.'
            });
        }

        btn.addEventListener('click', function(e) {
            e.preventDefault();
            // This control discloses a menu; it is not a navigation link. Every
            // page closes the mobile nav when an <a> inside it is clicked, and
            // on <=768px that nav is display:none unless .navbar-nav-open, so
            // letting the click bubble collapsed the panel containing this menu
            // the instant it opened (reproducible only when the tap landed on
            // the label rather than its inline SVG icon).
            e.stopPropagation();
            if (menu.hidden) openMenu();
            else closeMenu();
        });

        document.addEventListener('click', function(e) {
            if (menu.hidden) return;
            // Decide from the dispatch-time event path: choosing an option
            // re-renders the panel, which can detach e.target before this
            // listener runs and would otherwise close the menu we just used.
            var inside;
            if (typeof e.composedPath === 'function') {
                var path = e.composedPath();
                inside = path.indexOf(menu) !== -1 || path.indexOf(btn) !== -1;
            } else {
                inside = !e.target ||
                    menu.contains(e.target) ||
                    btn.contains(e.target);
            }
            if (!inside) closeMenu();
        });

        document.addEventListener('keydown', function(e) {
            if (e.key === 'Escape' && !menu.hidden) {
                closeMenu();
                btn.focus();
            }
        });
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initNavLogin);
    } else {
        initNavLogin();
    }

    return {
        showToast: showToast,
        showConfirmModal: showConfirmModal,
        renderAuthChoice: renderAuthChoice,
        renderEmailForm: renderEmailForm,
        initNavLogin: initNavLogin
    };
})();
