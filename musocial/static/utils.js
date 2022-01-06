function getCookie(name) {
    const value = `; ${document.cookie}`;
    const parts = value.split(`; ${name}=`);
    if (parts.length === 2) {
        return parts.pop().split(';').shift();
    }
}

function replaceClass(eId, cOld, cNew) {
    var e = document.getElementById(eId);
    if (e.classList.contains(cOld)) {
        e.classList.remove(cOld);
    }
    e.classList.add(cNew);
}

function hasParentWithClass(element, classNames) {
    for (const className of classNames) {
        if (element.classList && element.classList.contains(className)) {
            return true;
        }
    }
    return element.parentNode && hasParentWithClass(element.parentNode, classNames);
}

function buildXhr(successCB) {
    var xhr = new XMLHttpRequest();
    xhr.onreadystatechange = function() {
        if (xhr.readyState == 4 && xhr.status == 200)
        {
            var resp = JSON.parse(xhr.responseText);
            if (resp.ok) {
                successCB(resp);
            }
        }
    }
    return xhr;
}

function doPost(url, data, csrf_token, successCB) {
    var xhr = buildXhr(successCB);
    xhr.open('POST', url);
    xhr.setRequestHeader("Content-type", "application/x-www-form-urlencoded");
    var token = getCookie('csrf_access_token');
    xhr.send(`${data}&csrf_token=${csrf_token}&jwt_csrf_token=${token}`);
    return false;
}

function likeItem(itemId, value) {
    var item = document.getElementById('item-' + itemId);
    doPost(`/items/${itemId}/like`, `value=${value}`, item.dataset.csrf_token,
        function(_) {
            replaceClass(`item-${itemId}`, `item-liked-${1-value}`, `item-liked-${value}`);
        }
    );
}

function hideItem(itemId, value) {
    var item = document.getElementById('item-' + itemId);
    doPost(`/items/${itemId}/hide`, `value=${value}`, item.dataset.csrf_token,
        function(_) {
            replaceClass(`item-${itemId}`, `item-hidden-${1-value}`, `item-hidden-${value}`);
        }
    );
}

function followFeed(feedId, value, csrf_token) {
    doPost(`/feeds/${feedId}/follow`, `value=${value}`, csrf_token,
        function(_) {
            replaceClass(`feed-${feedId}`, `feed-followed-${1-value}`, `feed-followed-${value}`);
        }
    );
}

function followPodcast(podcastindex_id, url, homepage_url, title, csrf_token) {
    doPost("/feeds/podcasts/follow", `url=${url}&homepage_url=${homepage_url}&title=${title}`, csrf_token,
        function(_) {
            replaceClass(`podcast-${podcastindex_id}`, `feed-followed-0`, `feed-followed-1`);
        }
    );
}

function unfollowPodcast(podcastindex_id, url, csrf_token) {
    doPost("/feeds/podcasts/unfollow", `url=${url}`, csrf_token,
        function(_) {
            replaceClass(`podcast-${podcastindex_id}`, `feed-followed-1`, `feed-followed-0`);
        }
    );
}

function playPodcastItem(itemId) {
    for (const activeItem of document.querySelectorAll('.item-active')) {
        activeItem.classList.remove('item-active');
    }

    var item = document.getElementById('item-' + itemId);
    item.classList.add('item-active');

    var source = document.getElementById('audioSource');
    source.src = item.dataset.enclosure_url;
    source.type = item.dataset.enclosure_type;

    var player = document.getElementById('podcastPlayer');
    player.onended = function() {
        var currItem = null;
        var nextItem = null;
        for (const i of document.querySelectorAll('.item')) {
            if (i.dataset.id === itemId) {
                hideItem(itemId, 1, i.dataset.csrf_token);
                currItem = i;
                continue;
            }
            if (currItem) {
                nextItem = i;
                break;
            }
        }
        if (nextItem) {
            playPodcastItem(nextItem.dataset.id);
        } else {
            currItem.classList.remove('item-active');
        }
    }
    player.load();
    player.play();
}

function itemClick(e, itemId) {
    if (hasParentWithClass(e.target, ['like-link', 'unlike-link', 'hide-link', 'unhide-link', 'open-link'])) {
        return;
    }

    var item = document.getElementById('item-' + itemId);
    if (item.classList.contains('podcast')) {
        playPodcastItem(itemId);
    }
}

function feedClick(e, feedId, baseUrl) {
    if (hasParentWithClass(e.target, ['follow-link', 'unfollow-link'])) {
        return;
    }

    window.location = baseUrl + (feedId ? `?feed_id=${feedId}` : "");
}
