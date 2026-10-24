// Critique sharing — optional, user-initiated, and honest about it.
//
// Nothing here publishes anything. A platform link only opens that
// platform's own compose/share page with prefilled text, and a copy button
// only writes to the clipboard; every action happens because a person
// clicked it, and a compose window opening is never reported as a posted
// share.
//
// After a submission the success state stays compact: the confirmation, the
// project's title, one primary action (View project) and one secondary one
// (Share project). Everything for sharing lives behind that secondary action
// and stays collapsed until a person asks for it — the four compact actions
// (X, Reddit, Copy link, Copy post, each with a real, recognizable icon), the
// editable suggested post behind "Create a share post", and, where a browser
// offers the Web Share API, one extra "Share via device" control that opens
// that native sheet with the live post text. Where it does not, no extra
// control is rendered at all and Copy link remains the fallback, so every
// browser keeps the same four actions. The sheet opening is never reported as
// a posted share either — the page cannot see what the person chose to do
// with it, and dismissing it is a decision, not a failure.
//
// Share endpoints, each checked against live HTTP before use:
//   X      https://twitter.com/intent/tweet?text=…
//          (301 → x.com/intent/tweet, 200)
//   Reddit https://www.reddit.com/submit?url=…&title=… (200)
//
// The copy actions touch the clipboard only: the canonical project link
// (built from the origin that served the page) or the suggested post
// exactly as it stands, edits included.

var CritiqueShare = (function() {
    'use strict';

    // Inline icons: the official X and Reddit marks (simple-icons, CC0)
    // plus two plain line icons for the copy actions. These constants are
    // the ONLY strings ever assigned to innerHTML — never any user content —
    // so icon markup can never become an injection point. No icon library
    // or network fetch ships with them.
    var ICONS = {
        x: '<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true" focusable="false"><path d="M14.234 10.162 22.977 0h-2.072l-7.591 8.824L7.251 0H.258l9.168 13.343L.258 24H2.33l8.016-9.318L16.749 24h6.993zm-2.837 3.299-.929-1.329L3.076 1.56h3.182l5.965 8.532.929 1.329 7.754 11.09h-3.182z"/></svg>',
        reddit: '<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true" focusable="false"><path d="M12 0C5.373 0 0 5.373 0 12c0 3.314 1.343 6.314 3.515 8.485l-2.286 2.286C.775 23.225 1.097 24 1.738 24H12c6.627 0 12-5.373 12-12S18.627 0 12 0Zm4.388 3.199c1.104 0 1.999.895 1.999 1.999 0 1.105-.895 2-1.999 2-.946 0-1.739-.657-1.947-1.539v.002c-1.147.162-2.032 1.15-2.032 2.341v.007c1.776.067 3.4.567 4.686 1.363.473-.363 1.064-.58 1.707-.58 1.547 0 2.802 1.254 2.802 2.802 0 1.117-.655 2.081-1.601 2.531-.088 3.256-3.637 5.876-7.997 5.876-4.361 0-7.905-2.617-7.998-5.87-.954-.447-1.614-1.415-1.614-2.538 0-1.548 1.255-2.802 2.803-2.802.645 0 1.239.218 1.712.585 1.275-.79 2.881-1.291 4.64-1.365v-.01c0-1.663 1.263-3.034 2.88-3.207.188-.911.993-1.595 1.959-1.595Zm-8.085 8.376c-.784 0-1.459.78-1.506 1.797-.047 1.016.64 1.429 1.426 1.429.786 0 1.371-.369 1.418-1.385.047-1.017-.553-1.841-1.338-1.841Zm7.406 0c-.786 0-1.385.824-1.338 1.841.047 1.017.634 1.385 1.418 1.385.785 0 1.473-.413 1.426-1.429-.046-1.017-.721-1.797-1.506-1.797Zm-3.703 4.013c-.974 0-1.907.048-2.77.135-.147.015-.241.168-.183.305.483 1.154 1.622 1.964 2.953 1.964 1.33 0 2.47-.81 2.953-1.964.057-.137-.037-.29-.184-.305-.863-.087-1.795-.135-2.769-.135Z"/></svg>',
        link: '<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" focusable="false"><path d="M10 13a5 5 0 0 0 7.54.54l3-3a5 5 0 0 0-7.07-7.07l-1.72 1.71"/><path d="M14 11a5 5 0 0 0-7.54-.54l-3 3a5 5 0 0 0 7.07 7.07l1.71-1.71"/></svg>',
        copy: '<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" focusable="false"><rect x="9" y="9" width="13" height="13" rx="2"/><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/></svg>'
    };

    // The canonical public link, built from the origin that served the page
    // (critique.page in production) — never a hard-coded development URL.
    function projectUrl(projectId) {
        return window.location.origin + '/project/' + parseInt(projectId, 10);
    }

    function suggestedPost(title, url) {
        return 'I just shared my project, ' + title + ', on Critique and would love some honest feedback. What do you think, and what could I improve?\n\n' + url;
    }

    // Only fixed, verified hosts; everything that travels in a query string
    // is percent-encoded.
    function shareUrls(postText, title, url) {
        return {
            x: 'https://twitter.com/intent/tweet?text=' + encodeURIComponent(postText),
            reddit: 'https://www.reddit.com/submit?url=' + encodeURIComponent(url) + '&title=' + encodeURIComponent(title)
        };
    }

    function track(eventName, projectId) {
        var analytics = window.CritiqueAnalytics;
        if (analytics && typeof analytics.trackEvent === 'function') {
            analytics.trackEvent(eventName, projectId || null);
        }
    }

    function copyText(text, confirmation) {
        if (!navigator.clipboard || !navigator.clipboard.writeText) {
            CritiqueUI.showToast('Copying is not available in this browser', 'error');
            return Promise.resolve(false);
        }
        return navigator.clipboard.writeText(text).then(function() {
            CritiqueUI.showToast(confirmation, 'success');
            return true;
        }, function() {
            CritiqueUI.showToast('Could not copy. Try again.', 'error');
            return false;
        });
    }

    // The native share sheet, if this browser has one. The control is only
    // rendered when it does, so no browser is ever shown a button that opens
    // nothing — everything else keeps the four actions above as its fallback.
    function nativeShareSupported() {
        var nav = navigator;
        return !!(nav && typeof nav.share === 'function');
    }

    // Whether this exact payload can go to the sheet right now. `canShare` is
    // consulted wherever it exists (it can refuse a payload this browser will
    // not take), and a canShare that throws is answered the same way as one
    // that says no: fall back, never fail.
    function canNativeShare(payload) {
        if (!nativeShareSupported()) return false;
        if (typeof navigator.canShare !== 'function') return true;
        try {
            return navigator.canShare(payload) === true;
        } catch (e) {
            return false;
        }
    }

    function nativeSharePayload(data, getPost) {
        return { title: data.title, text: getPost(), url: data.url };
    }

    // The one control that opens the native sheet, carrying the post exactly
    // as it stands (edits included). It is built only where that sheet exists;
    // when the browser later refuses the payload it copies the link instead,
    // so the click is never a dead end. `label` (optional) names the control
    // where "Share project" is already taken — by the success state's
    // secondary action, which is what reveals this panel.
    function nativeShareAction(data, getPost, projectId, label) {
        if (!nativeShareSupported()) return null;

        var current = getPost || function() { return data.post; };
        var button = make('button', 'btn btn-primary share-native', label || 'Share project');
        button.type = 'button';
        button.title = 'Open your device share sheet';

        button.addEventListener('click', function() {
            var payload = nativeSharePayload(data, current);
            track('share_option_clicked', projectId);

            if (!canNativeShare(payload)) {
                // No sheet will take this: copy the link, exactly as the
                // Copy link action does, and confirm it the same way.
                copyText(data.url, 'Link copied');
                track('share_copy_link', projectId);
                return;
            }

            var shared;
            try {
                shared = navigator.share(payload);
            } catch (e) {
                CritiqueUI.showToast('Could not share. Copy the link instead.', 'error');
                return;
            }
            if (shared && typeof shared.then === 'function') {
                shared.then(function() {
                    // The sheet opened and closed. Nothing is reported here:
                    // we are not told whether anything was shared at all.
                }, function(err) {
                    // Dismissing the sheet is a person changing their mind,
                    // not a failure — say nothing rather than show a false
                    // error. (AbortError, or code 20 where Safari reports it
                    // that way.)
                    if (err && (err.name === 'AbortError' || err.code === 20)) return;
                    CritiqueUI.showToast('Could not share. Copy the link instead.', 'error');
                });
            }
        });

        return button;
    }

    function make(tag, className, text) {
        var node = document.createElement(tag);
        if (className) node.className = className;
        if (text !== undefined && text !== null) node.textContent = text;
        return node;
    }

    // The icon sits in a child span so the label can stay plain text on the
    // control itself; CSS (order: -1) renders the icon to its left.
    function withIcon(el, name) {
        var icon = make('span', 'share-icon');
        icon.innerHTML = ICONS[name];
        el.appendChild(icon);
        return el;
    }

    // A fixed-domain compose link: target=_blank with noopener, never a
    // user-controlled host, so it can neither hijack this tab nor become a
    // redirect. The visible label is also the accessible name.
    function externalShareLink(label, iconName, href, projectId) {
        var link = make('a', 'share-action', label);
        link.href = href;
        link.target = '_blank';
        link.rel = 'noopener noreferrer';
        link.title = 'Share on ' + label;
        link.setAttribute('aria-label', 'Share this project on ' + label);
        withIcon(link, iconName);
        link.addEventListener('click', function() {
            track('share_option_clicked', projectId);
        });
        return link;
    }

    function copyAction(iconName, label, getText, confirmation, eventName, projectId, hint) {
        var button = make('button', 'share-action', label);
        button.type = 'button';
        button.title = hint;
        withIcon(button, iconName);
        button.addEventListener('click', function() {
            copyText(getText(), confirmation);
            track(eventName, projectId);
        });
        return button;
    }

    // The four actions, compact and balanced: X, Reddit, Copy link, Copy post.
    // `getPost` (optional) returns the post text as it stands right now, so
    // an edited suggested post is what reaches the compose window or the
    // clipboard — the edit is never overwritten or ignored.
    function buildActions(data, getPost, extraClass) {
        var current = getPost || function() { return data.post; };
        var urls = shareUrls(current(), data.title, data.url);
        var grid = make('div', 'share-grid' + (extraClass ? ' ' + extraClass : ''));

        var xLink = externalShareLink('X', 'x', urls.x, data.projectId);
        xLink.addEventListener('click', function(e) {
            if (e && e.preventDefault) e.preventDefault();
            // Live text at click time; the href above stays as the no-JS and
            // right-click fallback built from the default post.
            window.open(
                'https://twitter.com/intent/tweet?text=' + encodeURIComponent(current()),
                '_blank',
                'noopener,noreferrer'
            );
        });
        grid.appendChild(xLink);

        grid.appendChild(externalShareLink('Reddit', 'reddit', urls.reddit, data.projectId));

        grid.appendChild(copyAction(
            'link', 'Copy link',
            function() { return data.url; },
            'Link copied', 'share_copy_link', data.projectId,
            'Copy the project link'
        ));
        grid.appendChild(copyAction(
            'copy', 'Copy post',
            current,
            'Post copied', 'share_copy_post', data.projectId,
            'Copy the suggested post'
        ));

        return grid;
    }

    // The post-submission success state. Called only after the API has
    // confirmed creation (201 with the created project), never before.
    //
    // It is deliberately compact — the confirmation, the title, one primary
    // action (View project) and one secondary one (Share project) — and the
    // sharing lives inside the section that secondary action reveals. The
    // controls are all built up front (so the copy actions and the editable
    // post stay addressable) but hidden until asked for; `share_ui_shown`
    // follows that truth and fires the first time the options really are on
    // screen, not when the confirmation appears.
    function renderSuccess(container, data) {
        var url = data.url || projectUrl(data.projectId);
        var defaultPost = suggestedPost(data.title, url);

        container.textContent = '';
        var panel = make('div', 'success-share');
        panel.setAttribute('role', 'status');

        panel.appendChild(make('h3', 'success-title', 'Your project is live'));
        panel.appendChild(make('p', 'success-lede', 'Your project is now on Critique.'));
        panel.appendChild(make('strong', 'success-project-title', data.title));

        // One primary action: the named destination (never the raw URL) the
        // whole confirmation is about.
        var link = make('a', 'btn btn-primary', 'View project');
        link.href = url;

        // One secondary action reveals the share options; the way onward
        // stays quiet beside them.
        var toggle = make('button', 'btn btn-secondary share-toggle', 'Share project');
        toggle.id = 'share-toggle';
        toggle.type = 'button';
        toggle.setAttribute('aria-expanded', 'false');
        toggle.setAttribute('aria-controls', 'share-section');

        var actions = make('div', 'success-actions');
        actions.appendChild(link);
        actions.appendChild(toggle);
        actions.appendChild(make('span', 'success-actions-spacer'));
        var myProjects = make('a', 'btn btn-ghost share-continue', 'Continue to My Projects');
        myProjects.href = '/my-projects';
        actions.appendChild(myProjects);
        panel.appendChild(actions);

        var share = make('section', 'share-section');
        share.id = 'share-section';
        share.hidden = true;
        share.setAttribute('aria-label', 'Share your project (optional)');

        // The suggested post is real but optional: it stays in the DOM (so
        // the copy and compose actions always carry the live text, edits
        // included) and is revealed only when someone asks to work on it.
        var postInput = make('textarea', 'share-post');
        postInput.value = defaultPost;
        postInput.setAttribute('aria-label', 'Suggested post — edit it before copying or sharing');
        postInput.setAttribute('rows', '4');
        var getLivePost = function() { return postInput.value || defaultPost; };

        var postWrap = make('div', 'share-post-wrap');
        postWrap.id = 'share-post-wrap';
        postWrap.hidden = true;
        postWrap.appendChild(make('p', 'share-post-label', 'Suggested post'));
        postWrap.appendChild(postInput);
        // Handle kept on the container so page scripts (and tests) can read or
        // edit the live post text without hunting through children.
        container.postInput = postInput;

        var postToggle = make('button', 'btn btn-ghost share-post-toggle', 'Create a share post');
        postToggle.id = 'share-post-toggle';
        postToggle.type = 'button';
        postToggle.setAttribute('aria-expanded', 'false');
        postToggle.setAttribute('aria-controls', 'share-post-wrap');
        postToggle.addEventListener('click', function() {
            var opening = postWrap.hidden;
            postWrap.hidden = !opening;
            postToggle.setAttribute('aria-expanded', opening ? 'true' : 'false');
        });

        // The native sheet sits above the four compact actions, so the
        // primary way to share comes first — under a name of its own, so it
        // can never be confused with the "Share project" toggle. Rendered
        // only where a browser has one; nothing changes where it does not.
        var nativeShare = nativeShareAction({
            projectId: data.projectId,
            title: data.title,
            url: url,
            post: defaultPost
        }, getLivePost, data.projectId, 'Share via device');
        if (nativeShare) share.appendChild(nativeShare);

        share.appendChild(buildActions({
            projectId: data.projectId,
            title: data.title,
            url: url,
            post: defaultPost
        }, getLivePost));
        share.appendChild(postToggle);
        share.appendChild(postWrap);
        panel.appendChild(share);

        var shareUiShown = false;
        toggle.addEventListener('click', function() {
            var opening = share.hidden;
            share.hidden = !opening;
            toggle.setAttribute('aria-expanded', opening ? 'true' : 'false');
            // The UI appeared; the clicks themselves are tracked where they
            // happen. One event, fired once, when the section first really
            // is on screen.
            if (opening && !shareUiShown) {
                shareUiShown = true;
                track('share_ui_shown', data.projectId);
            }
        });

        container.appendChild(panel);

        return panel;
    }

    // The inline share row on a My Projects card: the same four actions in a
    // balanced 2×2, sized for the card. `host` is where the row lives (the
    // card's info column in the page, any container in tests).
    function renderCardShareRow(host, data) {
        var url = projectUrl(data.projectId);
        var post = suggestedPost(data.title, url);

        var row = buildActions({
            projectId: data.projectId,
            title: data.title,
            url: url,
            post: post
        }, null, 'card-share');
        row.setAttribute('role', 'group');
        row.setAttribute('aria-label', 'Share ' + data.title);

        // Same native control above the card's four actions, and only where
        // the browser offers the sheet.
        var nativeShare = nativeShareAction({
            projectId: data.projectId,
            title: data.title,
            url: url,
            post: post
        }, null, data.projectId);
        if (nativeShare) host.appendChild(nativeShare);

        host.appendChild(row);
        track('share_ui_shown', data.projectId);
        return row;
    }

    return {
        projectUrl: projectUrl,
        suggestedPost: suggestedPost,
        shareUrls: shareUrls,
        renderSuccess: renderSuccess,
        renderCardShareRow: renderCardShareRow
    };
})();
