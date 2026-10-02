// Critique sharing — optional, user-initiated, and honest about it.
//
// Nothing here publishes anything. A platform link only opens that
// platform's own compose/share page with prefilled text, and a copy button
// only writes to the clipboard; every action happens because a person
// clicked it, and a compose window opening is never reported as a posted
// share.
//
// The panel offers exactly four compact actions — X, Reddit, Copy link,
// Copy post — each with a real, recognizable icon.
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
    function renderSuccess(container, data) {
        var url = data.url || projectUrl(data.projectId);
        var defaultPost = suggestedPost(data.title, url);

        container.textContent = '';
        var panel = make('div', 'success-share');
        panel.setAttribute('role', 'status');

        panel.appendChild(make('h3', 'success-title', 'Your project is live!'));
        panel.appendChild(make('p', 'success-lede',
            'Your project has been shared on Critique. Invite people to explore it and share their feedback.'));

        var summary = make('div', 'success-project');
        summary.appendChild(make('strong', 'success-project-title', data.title));
        if (data.description) {
            summary.appendChild(make('p', 'success-project-desc', data.description));
        }
        var link = make('a', 'success-link', url);
        link.href = url;
        summary.appendChild(link);

        if (data.questionText) {
            var question = make('div', 'success-question');
            question.appendChild(make('span', 'success-question-label', 'Your question'));
            question.appendChild(make('p', 'success-question-text', data.questionText));
            summary.appendChild(question);
        }
        panel.appendChild(summary);

        var share = make('section', 'share-section');
        share.id = 'share-section';
        share.setAttribute('aria-label', 'Share your project (optional)');
        share.appendChild(make('h4', 'share-title', 'Let more people discover your project'));
        share.appendChild(make('p', 'share-support',
            'Share your project with your community to reach more builders and get different perspectives.'));

        share.appendChild(make('p', 'share-post-label', 'Suggested post'));
        var postInput = make('textarea', 'share-post');
        postInput.value = defaultPost;
        postInput.setAttribute('aria-label', 'Suggested post — edit it before copying or sharing');
        postInput.setAttribute('rows', '4');
        share.appendChild(postInput);
        // Handle kept on the container so page scripts (and tests) can read or
        // edit the live post text without hunting through children.
        container.postInput = postInput;

        var getLivePost = function() { return postInput.value || defaultPost; };
        share.appendChild(buildActions({
            projectId: data.projectId,
            title: data.title,
            url: url,
            post: defaultPost
        }, getLivePost));

        // The way onward, quiet and apart from the sharing actions.
        var actions = make('div', 'share-actions');
        var skip = make('button', 'btn btn-ghost share-skip', 'Skip for now');
        skip.type = 'button';
        skip.addEventListener('click', function() {
            share.style.display = 'none';
            if (link && link.focus) link.focus();
        });
        actions.appendChild(skip);
        actions.appendChild(make('span', 'share-actions-spacer'));
        var myProjects = make('a', 'btn btn-secondary share-continue', 'Continue to My Projects');
        myProjects.href = '/my-projects';
        actions.appendChild(myProjects);
        share.appendChild(actions);

        panel.appendChild(share);
        container.appendChild(panel);

        // The UI appeared; the clicks themselves are tracked where they
        // happen. One event, fired once, when the section actually renders.
        track('share_ui_shown', data.projectId);

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
