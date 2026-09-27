"""
Lambda: verify_handler
Route: GET /documents/{hash}

Reads the smart contract's verifyDocument(bytes32) view function
directly via a raw JSON-RPC eth_call to Sepolia — no wallet or gas
needed, since this only reads public on-chain data.

This exists as a REST API alternative to the frontend's direct
ethers.js call — useful for any external service, script, or client
that wants to check a document's status without needing a Web3
library at all, just a plain HTTP GET.

Response (JSON):
{
  "hash": "0x...",
  "exists": true,
  "owner": "0x...",
  "timestamp": 1234567890
}
"""

import json
import os
import urllib.request

from eth_abi import decode
from Crypto.Hash import keccak

RPC_URL = os.environ["SEPOLIA_RPC_URL"]
CONTRACT_ADDRESS = os.environ["CONTRACT_ADDRESS"]

# Precomputed once at import time - function selector for verifyDocument(bytes32)
_VERIFY_SELECTOR = None


def handler(event, context):
    try:
        document_hash = event.get("pathParameters", {}).get("hash")

        if not document_hash:
            return _response(400, {"error": "hash path parameter is required"})

        if not document_hash.startswith("0x") or len(document_hash) != 66:
            return _response(400, {"error": "hash must be a 0x-prefixed 32-byte hex string"})

        exists, owner, timestamp = _verify_document_onchain(document_hash)

        return _response(200, {
            "hash": document_hash,
            "exists": exists,
            "owner": owner,
            "timestamp": timestamp,
        })

    except Exception as e:
        return _response(500, {"error": str(e)})


def _function_selector(signature: str) -> str:
    global _VERIFY_SELECTOR
    if _VERIFY_SELECTOR is None:
        k = keccak.new(digest_bits=256)
        k.update(signature.encode())
        _VERIFY_SELECTOR = k.hexdigest()[:8]
    return _VERIFY_SELECTOR


def _verify_document_onchain(document_hash_hex: str):
    selector = _function_selector("verifyDocument(bytes32)")

    hash_bytes = bytes.fromhex(document_hash_hex[2:])  # strip "0x"
    from eth_abi import encode as abi_encode
    encoded_args = abi_encode(["bytes32"], [hash_bytes])
    calldata = "0x" + selector + encoded_args.hex()

    rpc_payload = {
        "jsonrpc": "2.0",
        "method": "eth_call",
        "params": [
            {"to": CONTRACT_ADDRESS, "data": calldata},
            "latest",
        ],
        "id": 1,
    }

    req = urllib.request.Request(
        RPC_URL,
        data=json.dumps(rpc_payload).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    with urllib.request.urlopen(req, timeout=10) as resp:
        result = json.loads(resp.read())

    if "error" in result:
        raise RuntimeError(f"RPC error: {result['error']}")

    raw_result = result["result"]
    result_bytes = bytes.fromhex(raw_result[2:])  # strip "0x"

    exists, owner, timestamp = decode(["bool", "address", "uint256"], result_bytes)
    return exists, owner, timestamp


def _response(status_code: int, body: dict):
    return {
        "statusCode": status_code,
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*",  # tighten to your frontend's real origin before production use
        },
        "body": json.dumps(body),
    }