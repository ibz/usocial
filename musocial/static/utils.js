// NB: VALUE_HEARTBEAT_DELAY * VALUE_HEARTBEAT_COUNT should always be 60000 (1 minute)
// see: https://github.com/Podcastindex-org/podcast-namespace/blob/main/value/value.md#payment-intervals
VALUE_HEARTBEAT_DELAY = 1000;
VALUE_HEARTBEAT_COUNT = 60;

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

function likeItem(feedId, itemId, value) {
    var item = document.getElementById('item-' + itemId);
    doPost(`/feeds/${feedId}/items/${itemId}/like`, `value=${value}`, item.dataset.csrf_token,
        function(_) {
            replaceClass(`item-${itemId}`, `item-liked-${1-value}`, `item-liked-${value}`);
        }
    );
}

function hideItem(feedId, itemId, value) {
    var item = document.getElementById('item-' + itemId);
    doPost(`/feeds/${feedId}/items/${itemId}/hide`, `value=${value}`, item.dataset.csrf_token,
        function(_) {
            replaceClass(`item-${itemId}`, `item-hidden-${1-value}`, `item-hidden-${value}`);
        }
    );
}

function playedItemValue(feedId, itemId, value) {
    var item = document.getElementById('item-' + itemId);
    doPost(`/feeds/${feedId}/items/${itemId}/played-value`, `value=${value}`, item.dataset.csrf_token,
        function(_) { });
}

function followFeed(feedId, value, csrf_token) {
    doPost(`/feeds/${feedId}/follow`, `value=${value}`, csrf_token,
        function(_) {
            replaceClass(`feed-${feedId}`, `feed-followed-${1-value}`, `feed-followed-${value}`);
        }
    );
}

function followPodcast(podcastindex_id, url, homepage_url, title, csrf_token) {
    var followLink = document.querySelector(`#podcast-${podcastindex_id} .follow-link span`);
    var oldContent = followLink.innerHTML;
    var oldCB = followLink.onclick;
    followLink.textContent = "...";
    followLink.onclick = function() { return false; };
    doPost("/feeds/podcasts/follow", `url=${url}&homepage_url=${homepage_url}&title=${title}`, csrf_token,
        function(_) {
            replaceClass(`podcast-${podcastindex_id}`, `feed-followed-0`, `feed-followed-1`);
            followLink.onclick = oldCB;
            followLink.innerHTML = oldContent;
        }
    );
}

function unfollowPodcast(podcastindex_id, url, csrf_token) {
    var unfollowLink = document.querySelector(`#podcast-${podcastindex_id} .unfollow-link span`);
    var oldContent = unfollowLink.innerHTML;
    var oldCB = unfollowLink.onclick;
    unfollowLink.textContent = "...";
    unfollowLink.onclick = function() { return false; };
    doPost("/feeds/podcasts/unfollow", `url=${url}`, csrf_token,
        function(_) {
            replaceClass(`podcast-${podcastindex_id}`, `feed-followed-1`, `feed-followed-0`);
            unfollowLink.onclick = oldCB;
            unfollowLink.innerHTML = oldContent;
        }
    );
}

function valueHeartbeat(feedId, itemId) {
    var player = document.getElementById('podcastPlayer');
    if (player.duration > 0 && !player.paused) {
        if (!player.valueHeartbeatCount) {
            player.valueHeartbeatCount = 0;
        }
        player.valueHeartbeatCount += 1;
        if (player.valueHeartbeatCount == VALUE_HEARTBEAT_COUNT) {
            playedItemValue(feedId, itemId, 1);
            player.valueHeartbeatCount = 0;
        }
        setTimeout(function() { valueHeartbeat(feedId, itemId) }, VALUE_HEARTBEAT_DELAY);
    }
}

function playPodcastItem(feedId, itemId) {
    for (const activeItem of document.querySelectorAll('.item-active')) {
        activeItem.classList.remove('item-active');
    }

    var item = document.getElementById('item-' + itemId);
    item.classList.add('item-active');

    var source = document.getElementById('audioSource');
    source.src = item.dataset.enclosure_url;
    source.type = item.dataset.enclosure_type;

    var player = document.getElementById('podcastPlayer');
    player.onplay = function() {
        if (item.dataset.has_value_spec) {
            setTimeout(function() { valueHeartbeat(feedId, itemId) }, VALUE_HEARTBEAT_DELAY);
        }
    }
    player.onended = function() {
        var currItem = null;
        var nextItem = null;
        for (const i of document.querySelectorAll('.item')) {
            if (parseInt(i.dataset.id) === itemId) {
                hideItem(feedId, itemId, 1, i.dataset.csrf_token);
                currItem = i;
                continue;
            }
            if (currItem) {
                nextItem = i;
                break;
            }
        }
        if (nextItem) {
            playPodcastItem(nextItem.dataset.feed_id, nextItem.dataset.id);
        } else {
            currItem.classList.remove('item-active');
        }
    }
    player.load();
    player.play();
}

function itemClick(e, feedId, itemId) {
    if (hasParentWithClass(e.target, ['like-link', 'unlike-link', 'hide-link', 'unhide-link', 'open-link'])) {
        return;
    }

    var item = document.getElementById('item-' + itemId);
    if (item.classList.contains('podcast')) {
        playPodcastItem(feedId, itemId);
    }
}

function feedClick(e, feedId, liked) {
    if (hasParentWithClass(e.target, ['follow-link', 'unfollow-link'])) {
        return;
    }

    window.location = `/feeds/${feedId ? feedId : "all"}/items` + (liked ? '/liked' : '');
}
