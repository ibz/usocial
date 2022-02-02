from hashlib import sha256
import json
import os
import secrets

from lndgrpc import LNDClient

from usocial.main import app

import config

KEYSEND_PREIMAGE = 5482373484
PODCAST = 7629169

APP_NAME = 'usocial'

class PaymentFailed(Exception):
    def __init__(self, custom_records, message):
        self.custom_records = custom_records
        super().__init__(message)

def get_lnd_client():
    if not all([config.LND_IP, config.LND_GRPC_PORT, config.LND_DIR]):
        return None
    return LNDClient("%s:%s" % (config.LND_IP, config.LND_GRPC_PORT),
        macaroon_filepath=os.path.join(config.LND_DIR, "data/chain/bitcoin/mainnet/admin.macaroon"),
        cert_filepath=os.path.join(config.LND_DIR, "tls.cert"))

def get_podcast_tlv(value_msat, user, action, feed, item=None, ts=None):
    tlv = {
        'value_msat': value_msat,
        'sender_name': user.username,
        'action': action,
        'podcast': feed.title,
        'url': feed.url,
        'app_name': APP_NAME,
    }
    if item:
        tlv['episode'] = item.title
    if ts is not None:
        tlv['ts'] = ts
    return tlv

def send_payment(recipient, amount_msat, podcast_tlv):
    custom_records = {}
    if podcast_tlv:
        custom_records[PODCAST] = podcast_tlv
        total_tlv_value_msat = sum(t['value_msat'] for t in (podcast_tlv if isinstance(podcast_tlv, list) else [podcast_tlv]))
        if total_tlv_value_msat != amount_msat:
            app.logger.warn("Sum of values described in TLV (%s) does not match the actual amount sent (%s)." % (total_tlv_value_msat, amount_msat))
    if recipient.custom_key:
        try:
            custom_key = int(recipient.custom_key)
        except ValueError:
            custom_key = recipient.custom_key
        if custom_key not in custom_records:
            custom_records[custom_key] = recipient.custom_value or ""

    lnd = get_lnd_client()
    if not lnd:
        raise PaymentFailed(custom_records, "LND not configured.")

    encoded_custom_records = {}
    for k, v in custom_records.items():
        if isinstance(v, dict) or isinstance(v, list):
            encoded_custom_records[k] = json.dumps(v).encode('utf-8')
        elif isinstance(v, str):
            encoded_custom_records[k] = v.encode('utf-8')
        else:
            encoded_custom_records[k] = v

    preimage = secrets.token_bytes(32)
    encoded_custom_records[KEYSEND_PREIMAGE] = preimage

    ret = lnd.send_payment_v2(dest=bytes.fromhex(recipient.address), amt_msat=amount_msat,
        dest_custom_records=encoded_custom_records,
        payment_hash=sha256(preimage).digest(),
        timeout_seconds=10, fee_limit_msat=100000, max_parts=1, final_cltv_delta=144)

    app.logger.info("Sending %s (%s sats) to %s. Custom records: %s. Return value: %s." % (amount_msat, amount_msat / 1000, recipient.address, custom_records, ret))

    # TODO: deal with return value (also see PR https://github.com/kornpow/lnd-grpc-client/pull/3)
    # TODO: raise PaymentFailed for failed payments
