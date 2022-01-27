from hashlib import sha256
import json
import os
import secrets

from lndgrpc import LNDClient

from usocial.main import app

import config

KEYSEND_PREIMAGE = 5482373484
PODCAST = 7629169

APP_NAME = 'usocial.me'

class PaymentFailed(Exception):
    pass

def get_lnd_client():
    if not all([config.LND_IP, config.LND_GRPC_PORT, config.LND_DIR]):
        return None
    return LNDClient("%s:%s" % (config.LND_IP, config.LND_GRPC_PORT),
        macaroon_filepath=os.path.join(config.LND_DIR, "data/chain/bitcoin/mainnet/admin.macaroon"),
        cert_filepath=os.path.join(config.LND_DIR, "tls.cert"))

def send_stream_payment(address, amount, user_items):
    lnd = get_lnd_client()
    if not lnd:
        raise PaymentFailed("LND not configured.")
    preimage = secrets.token_bytes(32)
    tlv = []
    for user_item in user_items:
        tlv.append({
            'podcast': user_item.item.feed.title,
            'url': user_item.item.feed.url,
            'episode': user_item.item.title,
            'action': 'stream',
            'value_msat': int(amount * 1000 / len(user_items)), # TODO: improve split
            'app_name': APP_NAME,
            'sender_name': user_item.user.username,
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

    # TODO: deal with return value (also see PR https://github.com/kornpow/lnd-grpc-client/pull/3)
    # TODO: raise PaymentFailed for failed payments
