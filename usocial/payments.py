from hashlib import sha256
import json
import os
import secrets

from lndgrpc import LNDClient

from usocial.main import app

import config

KEYSEND_PREIMAGE = 5482373484
PODCAST = 7629169

ACTION_STREAM = 'stream'
ACTION_BOOST = 'boost'

APP_NAME = 'usocial.me'

def send_payment(address, amount, action, user_items):
    lnd = LNDClient("%s:%s" % (config.LND_IP, config.LND_GRPC_PORT),
        macaroon_filepath=os.path.join(config.LND_DIR, "data/chain/bitcoin/mainnet/admin.macaroon"),
        cert_filepath=os.path.join(config.LND_DIR, "tls.cert"))
    preimage = secrets.token_bytes(32)
    tlv = []
    for user_item in user_items:
        item = user_item.item
        tlv.append({
            'podcast': item.feed.title,
            'url': item.feed.url,
            'episode': item.title,
            'ts': user_item.play_position,
            'value_msat': amount * 1000 / len(user_items), # TODO: improve split
            'action': action,
            'sender_name': user_item.user.username,
            'app_name': APP_NAME,
        })
    if len(tlv) == 1:
        tlv = tlv[0]
    custom_records = {KEYSEND_PREIMAGE: preimage}
    if tlv:
        custom_records.update({PODCAST: json.dumps(tlv).encode('utf-8')})
    ret = lnd.send_payment_v2(dest=bytes.fromhex(address), amt=amount,
        dest_custom_records=custom_records,
        payment_hash=sha256(preimage).digest(),
        timeout_seconds=10, fee_limit_msat=100000, max_parts=1, final_cltv_delta=144)

    app.logger.info("Sending %s sats to %s. Custom records: %s. Return value: %s" % (amount, address, custom_records, ret))
