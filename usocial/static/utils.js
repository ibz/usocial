// NB: PODCAST_HEARTBEAT_DELAY * PODCAST_VALUE_HEARTBEAT_COUNT should always be 60000 (1 minute)
// see: https://github.com/Podcastindex-org/podcast-namespace/blob/main/value/value.md#payment-intervals
PODCAST_HEARTBEAT_DELAY = 1000;
PODCAST_VALUE_HEARTBEAT_COUNT = 60;

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

function buildXhr(successCB, errorCB) {
    var xhr = new XMLHttpRequest();
    xhr.onreadystatechange = function() {
        if (xhr.readyState == 4 && xhr.status == 200)
        {
            var resp = JSON.parse(xhr.responseText);
            if (resp.ok) {
                successCB(resp);
            } else {
                if (errorCB) {
                    errorCB(resp);
                }
            }
        }
    }
    return xhr;
}

function doPost(url, data, successCB, errorCB) {
    var xhr = buildXhr(successCB, errorCB);
    xhr.open('POST', url);
    xhr.setRequestHeader("Content-type", "application/x-www-form-urlencoded");
    var token = getCookie('csrf_access_token');
    xhr.send(`${data}&csrf_token=${csrfToken}&jwt_csrf_token=${token}`);
    return false;
}

function likeItem(feedId, itemId, value) {
    doPost(`/feeds/${feedId}/items/${itemId}/like`, `value=${value}`,
        function(_) {
            replaceClass(`item-${itemId}`, `item-liked-${1-value}`, `item-liked-${value}`);
        }
    );
}

function hideItem(feedId, itemId, value) {
    doPost(`/feeds/${feedId}/items/${itemId}/hide`, `value=${value}`,
        function(_) {
            replaceClass(`item-${itemId}`, `item-hidden-${1-value}`, `item-hidden-${value}`);
        }
    );
}

function updatePodcastItemPosition(feedId, itemId, position) {
    document.getElementById('item-' + itemId).dataset.play_position = position.toString();
    doPost(`/feeds/${feedId}/items/${itemId}/position`, `value=${position}`, function(_) { });
}

function playedItemValue(feedId, itemId, value) {
    var el_played_minutes = document.getElementById('stream-value-played');
    var playedMinutes = parseInt(el_played_minutes.innerText);
    el_played_minutes.innerText = (playedMinutes + value).toString();
    doPost(`/feeds/${feedId}/items/${itemId}/played-value`, `value=${value}`, function(_) { });
}

function sendBoostValue() {
    var source = document.getElementById('audioSource');
    var feedId = null, itemId = null;
    for (const item of document.querySelectorAll(".item")) {
        if (source.src === item.dataset.enclosure_url) {
            feedId = item.dataset.feed_id;
            itemId = item.dataset.id;
        }
    }
    if (itemId) {
        var player = document.getElementById('podcastPlayer');
        var ts = parseInt(player.currentTime);
        var amount = parseInt(document.getElementById('boost-value-amount').value);
        sendValue(feedId, itemId, 'boost', amount, ts, document.getElementById('send-boost-value'));
    }
}

function sendStreamValue(feedId) {
    var amount = parseInt(document.getElementById('stream-value-amount').value);
    sendValue(feedId, null, 'stream', amount, null, document.getElementById('send-stream-value'));
}

function sendValue(feedId, itemId, action, amount, ts, button) {
    button.style.display = 'none';
    var player = document.getElementById('podcastPlayer');
    var postUrl = `/feeds/${feedId}` + (itemId ? `/items/${itemId}` : "") + "/send-value";
    var params = `action=${action}&amount=${amount}` + (ts ? `&ts=${ts}` : "");
    doPost(postUrl, params,
        function(response) {
            var contributionAmount = document.getElementById(`contribution-amount-${action}`);
            contributionAmount.innerText = (parseInt(contributionAmount.innerText) + amount).toString();

            if (action === 'stream') {
                document.getElementById('stream-value-paid').innerText = document.getElementById('stream-value-played').innerText;
            }

            var feedDetailsBody = document.getElementById('feed-details').getElementsByTagName('tbody')[0];
            var row = feedDetailsBody.insertRow();
            row.className = "actionRow";
            var existingActionsVisible = false;
            for(const row of document.querySelectorAll('.actionRow')) {
                if (row.style.display === "table-row") {
                    existingActionsVisible = true;
                }
            }
            if (!existingActionsVisible) {
                row.style.display = 'none';
            }
            row.insertCell();

            var extra = response.has_errors ? '<i class="fas fa-exclamation" title="has errors"></i>' : "";
            var d = new Date();
            var formattedDate = d.toLocaleString('default', { day: 'numeric' }) + " " + d.toLocaleString('default', { month: 'short' }) + " " + d.toLocaleString('default', { year: 'numeric' });
            var formattedTime = d.toLocaleString('default', { hour12: false, hour: 'numeric', minute: 'numeric' });
            row.insertCell().innerHTML = `<small>${formattedDate} ${formattedTime}</small> ${extra} ${action} ${amount} sats`;
            button.style.display = 'inline';
        },
        function(_) {
            button.style.display = 'inline';
            alert("Send failed!");
        });
}

function followFeed(feedId, value) {
    doPost(`/feeds/${feedId}/follow`, `value=${value}`,
        function(_) {
            replaceClass(`feed-${feedId}`, `feed-followed-${1-value}`, `feed-followed-${value}`);
        }
    );
}

function followPodcast(podcastindex_id, url, homepage_url, title) {
    var followLink = document.querySelector(`#podcast-${podcastindex_id} .follow-link span`);
    var oldContent = followLink.innerHTML;
    var oldCB = followLink.onclick;
    followLink.textContent = "...";
    followLink.onclick = function() { return false; };
    doPost("/feeds/podcasts/follow", `url=${url}&homepage_url=${homepage_url}&title=${title}`,
        function(_) {
            replaceClass(`podcast-${podcastindex_id}`, `feed-followed-0`, `feed-followed-1`);
            followLink.onclick = oldCB;
            followLink.innerHTML = oldContent;
        }
    );
}

function unfollowPodcast(podcastindex_id, url) {
    var unfollowLink = document.querySelector(`#podcast-${podcastindex_id} .unfollow-link span`);
    var oldContent = unfollowLink.innerHTML;
    var oldCB = unfollowLink.onclick;
    unfollowLink.textContent = "...";
    unfollowLink.onclick = function() { return false; };
    doPost("/feeds/podcasts/unfollow", `url=${url}`,
        function(_) {
            replaceClass(`podcast-${podcastindex_id}`, `feed-followed-1`, `feed-followed-0`);
            unfollowLink.onclick = oldCB;
            unfollowLink.innerHTML = oldContent;
        }
    );
}

function podcastHeartbeat(feedId, itemId) {
    var player = document.getElementById('podcastPlayer');
    if (player.duration > 0 && !player.paused) {
        var source = document.getElementById('audioSource');
        var item = document.getElementById('item-' + itemId);

        if (source.src === item.dataset.enclosure_url) { // currently playing item could have changed in the last second!
            updatePodcastItemPosition(feedId, itemId, player.currentTime);
        }

        if (item.dataset.has_value_spec) {
            if (!player.valueHeartbeatCount) {
                player.valueHeartbeatCount = 0;
            }
            player.valueHeartbeatCount += 1;
            if (player.valueHeartbeatCount == PODCAST_VALUE_HEARTBEAT_COUNT) {
                playedItemValue(feedId, itemId, 1);
                player.valueHeartbeatCount = 0;
            }
        }
        setTimeout(function() { podcastHeartbeat(feedId, itemId) }, PODCAST_HEARTBEAT_DELAY);
    }
}

function playPodcastItem(feedId, itemId) {
    for (const activeItem of document.querySelectorAll('.item-active')) {
        activeItem.classList.remove('item-active');
    }

    var item = document.getElementById('item-' + itemId);
    item.classList.add('item-active');

    var boost = document.getElementById('boost-payment');
    if (boost) {
        boost.style.display = "table-row";
    }

    var source = document.getElementById('audioSource');
    source.src = item.dataset.enclosure_url;
    source.type = item.dataset.enclosure_type;

    var player = document.getElementById('podcastPlayer');
    player.onplay = function() {
        setTimeout(function() { podcastHeartbeat(feedId, itemId) }, PODCAST_HEARTBEAT_DELAY);
    }
    player.onended = function() {
        var currItem = null;
        var nextItem = null;
        for (const i of document.querySelectorAll('.item')) {
            if (parseInt(i.dataset.id) === itemId) {
                hideItem(feedId, itemId, 1);
                currItem = i;
                continue;
            }
            if (currItem) {
                nextItem = i;
                break;
            }
        }
        if (boost) {
            boost.style.display = "none";
        }
        if (nextItem) {
            playPodcastItem(nextItem.dataset.feed_id, nextItem.dataset.id);
        } else {
            currItem.classList.remove('item-active');
        }
    }
    player.load();
    player.currentTime = parseFloat(item.dataset.play_position);
    player.play();
}

function podcastPlayerVolumeChanged() {
    var player = document.getElementById('podcastPlayer');
    doPost(`/account/volume`, `value=${player.volume}`, function(_) { });
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

function showStreamPayment() {
    var streamRow = document.getElementById('stream-payment');
    streamRow.style.display = streamRow.style.display === "none" ? "table-row" : "none";
    var paymentAmount = parseInt(document.getElementById('value-spec-amount').innerText) * (parseInt(document.getElementById('stream-value-played').innerText) - parseInt(document.getElementById('stream-value-paid').innerText));
    document.getElementById('stream-value-amount').value = paymentAmount.toString();
}

function showActions() {
    for(const row of document.querySelectorAll('.actionRow')) {
        row.style.display = row.style.display === "none" ? "table-row" : "none";
    }
}

function onBodyLoad() {
    var player = document.getElementById('podcastPlayer');
    if (player) {
        player.volume = parseFloat(player.dataset.volume);
    }
    if (username && userTimezone === '') {
        var tz = Intl.DateTimeFormat().resolvedOptions().timeZone;
        doPost(`/account/timezone`, `value=${tz}`, function(_) { });
    }
}
