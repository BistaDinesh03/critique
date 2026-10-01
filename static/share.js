// Critique sharing — optional, user-initiated, and honest about it.
//
// Nothing here publishes anything. A platform link only opens that
// platform's own compose/share page with prefilled text, and a copy button
// only writes to the clipboard; every action happens because a person
// clicked it, and a compose window opening is never reported as a posted
// share.
//
// Share endpoints, each checked against live HTTP before use:
//   X        https://twitter.com/intent/tweet?text=…
//            (301 → x.com/intent/tweet, 200)
//   LinkedIn https://www.linkedin.com/sharing/share-offsite/?url=…
//            (LinkedIn's API-side posting needs OAuth, which we never touch)
//   Reddit   https://www.reddit.com/submit?url=…&title=… (200)
// Threads has no publicly verifiable web compose URL — signed-out requests
// only ever reach a generic login shell — so "Threads" copies the suggested
// post instead of pretending an intent endpoint exists.

var CritiqueShare = (function() {
    'use strict';

    var THREADS_HINT = 'Suggested post copied. Paste it into Threads.';

    // The canonical public link, built from the origin that served the page
    // (critique.page in production) — never a hard-coded development URL.
    function projectUrl(projectId) {
        return window.location.origin + '/project/' + parseInt(projectId, 10);
    }

    function suggestedPost(title, url) {
        return 'I just shared my project, ' + title + ', on Critique and would love some honest feedback. What do you think, and what could I improve?\n\n' + url;
    }

    function shareUrls(postText, title, url) {
        return {
            x: 'https://twitter.com/intent/tweet?text=' + encodeURIComponent(postText),
            linkedin: 'https://www.linkedin.com/sharing/share-offsite/?url=' + encodeURIComponent(url),
            reddit: 'https://www.reddit.com/submit?url=' + encodeURIComponent(url) + '&title=' + encodeURIComponent(title)
        };
    }

    function track(eventName, projectId) {
        var analytics = window.CritiqueAnalytics;
        if (analytics && typeof analytics.trackEvent === 'function') {
            analytics.trackEvent(eventName, projectId || null);
        }
    }

    function copyText(text, message) {
        if (!navigator.clipboard || !navigator.clipboard.writeText) {
            CritiqueUI.showToast('Copying is not available in this browser', 'error');
            return Promise.resolve(false);
        }
        return navigator.clipboard.writeText(text).then(function() {
            CritiqueUI.showToast(message, 'success');
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

    // A fixed-domain compose link: target=_blank with noopener, never a
    // user-controlled host, so it can neither hijack this tab nor become a
    // redirect.
    function externalShareLink(label, href, projectId) {
        var link = make('a', 'share-platform', label);
        link.href = href;
        link.target = '_blank';
        link.rel = 'noopener noreferrer';
        link.setAttribute('aria-label', 'Share this project on ' + label);
        link.addEventListener('click', function() {
            track('share_option_clicked', projectId);
        });
        return link;
    }

    // X, LinkedIn, Reddit and the Threads copy fallback in one row.
    // `getPost` (optional) returns the post text as it stands right now, so
    // an edited suggested post is what reaches the compose window — the edit
    // is never overwritten or ignored.
    function buildPlatformRow(data, getPost) {
        var current = getPost || function() { return data.post; };
        var urls = shareUrls(current(), data.title, data.url);
        var row = make('div', 'share-platforms');

        var xLink = externalShareLink('X', urls.x, data.projectId);
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
        row.appendChild(xLink);

        row.appendChild(externalShareLink('LinkedIn', urls.linkedin, data.projectId));
        row.appendChild(externalShareLink('Reddit', urls.reddit, data.projectId));

        var threads = make('button', 'share-platform', 'Copy for Threads');
        threads.type = 'button';
        threads.addEventListener('click', function() {
            copyText(current(), THREADS_HINT);
            track('share_copy_post', data.projectId);
        });
        row.appendChild(threads);

        return row;
    }

    function copyLinkButton(label, textToCopy, projectId) {
        var button = make('button', 'btn btn-secondary share-copy', label);
        button.type = 'button';
        button.addEventListener('click', function() {
            copyText(textToCopy(), 'Project link copied');
            track('share_copy_link', projectId);
        });
        return button;
    }

    function copyPostButton(label, getPost, projectId) {
        var button = make('button', 'btn btn-secondary share-copy', label);
        button.type = 'button';
        button.addEventListener('click', function() {
            copyText(getPost(), 'Suggested post copied');
            track('share_copy_post', projectId);
        });
        return button;
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
        share.appendChild(buildPlatformRow({
            projectId: data.projectId,
            title: data.title,
            url: url,
            post: defaultPost
        }, getLivePost));

        var actions = make('div', 'share-actions');
        actions.appendChild(copyLinkButton('Copy project link', function() { return url; }, data.projectId));
        actions.appendChild(copyPostButton('Copy suggested post', getLivePost, data.projectId));

        var spacer = make('span', 'share-actions-spacer');
        actions.appendChild(spacer);

        var skip = make('button', 'btn btn-ghost share-skip', 'Skip for now');
        skip.type = 'button';
        skip.addEventListener('click', function() {
            share.style.display = 'none';
            if (link && link.focus) link.focus();
        });
        actions.appendChild(skip);

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

    // The inline share row on a My Projects card. `host` is where the row
    // lives (the card's info column in the page, any container in tests).
    function renderCardShareRow(host, data) {
        var url = projectUrl(data.projectId);
        var post = suggestedPost(data.title, url);

        var row = make('div', 'card-share');
        row.setAttribute('role', 'group');
        row.setAttribute('aria-label', 'Share ' + data.title);
        row.appendChild(buildPlatformRow({
            projectId: data.projectId,
            title: data.title,
            url: url,
            post: post
        }, null));

        var copies = make('div', 'card-share-copies');
        copies.appendChild(copyLinkButton('Copy link', function() { return url; }, data.projectId));
        copies.appendChild(copyPostButton('Copy post', function() { return post; }, data.projectId));
        row.appendChild(copies);

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
