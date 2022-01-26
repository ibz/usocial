from hashlib import sha256
import os
import secrets

from lndgrpc import LNDClient

import config

KEY_SEND_PREIMAGE_TYPE = 5482373484

def send_payment(address, amount):
    lnd = LNDClient("%s:%s" % (config.LND_IP, config.LND_GRPC_PORT),
        macaroon_filepath=os.path.join(config.LND_DIR, "data/chain/bitcoin/mainnet/admin.macaroon"),
        cert_filepath=os.path.join(config.LND_DIR, "tls.cert"))
    preimage = secrets.token_bytes(32)
    lnd.send_payment_v2(dest=bytes.fromhex(address), amt=amount,
        dest_custom_records={KEY_SEND_PREIMAGE_TYPE: preimage},
        payment_hash=sha256(preimage).digest(),
        timeout_seconds=10, fee_limit_msat=100000, max_parts=1, final_cltv_delta=144)
