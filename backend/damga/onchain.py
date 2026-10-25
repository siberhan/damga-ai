"""Sends DamgaRegistry transactions on Sepolia with the relayer key (spec section 7)."""
import os
from typing import Any, Dict, List, Optional

from eth_account import Account
from web3 import Web3

from damga.chain import get_contract_abi, get_registry_address, get_web3_client, sign_plant_declaration

# Sepolia caps one transaction at 2^24 gas (EIP-7825).
TX_GAS_CAP = 16_777_216


def _b32(hex_str: str) -> bytes:
    return bytes.fromhex(hex_str[2:] if hex_str.startswith("0x") else hex_str).rjust(32, b"\0")


def _w3() -> Web3:
    w3 = get_web3_client()
    if w3 is None:
        raise RuntimeError("No Sepolia RPC configured")
    return w3


def registry(w3: Optional[Web3] = None):
    w3 = w3 or _w3()
    return w3.eth.contract(address=Web3.to_checksum_address(get_registry_address()), abi=get_contract_abi())


def _relayer() -> Any:
    key = os.environ.get("RELAYER_PRIVATE_KEY", "").strip()
    if not key:
        raise RuntimeError("RELAYER_PRIVATE_KEY is not set")
    return Account.from_key(key)


def _send(fn) -> Dict[str, Any]:
    """Estimates on the node (local EVMs underprice Sepolia storage), signs, sends, waits."""
    w3 = _w3()
    acct = _relayer()
    gas = min(int(fn.estimate_gas({"from": acct.address}) * 1.2), TX_GAS_CAP)
    base = w3.eth.get_block("latest")["baseFeePerGas"]
    tip = w3.to_wei(1, "gwei")
    tx = fn.build_transaction({
        "from": acct.address,
        "nonce": w3.eth.get_transaction_count(acct.address, "pending"),
        "gas": gas,
        "maxPriorityFeePerGas": tip,
        "maxFeePerGas": base * 2 + tip,
        "chainId": 11155111,
    })
    signed = acct.sign_transaction(tx)
    tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)
    receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=180)
    if receipt["status"] != 1:
        raise RuntimeError(f"Transaction reverted: {tx_hash.hex()}")
    return {"tx_hash": "0x" + tx_hash.hex().removeprefix("0x"), "receipt": receipt}


def register_file(plant_id_hex: str, year: int, cn_code: str) -> Optional[str]:
    """Registers the file once; returns the tx hash, or None when it already exists."""
    reg = registry()
    file_key = Web3.keccak(Web3().codec.encode(["bytes32", "uint16", "uint32"], [_b32(plant_id_hex), year, int(cn_code)]))
    if reg.functions.getFile(file_key).call()[5]:
        return None
    return _send(reg.functions.registerFile(_b32(plant_id_hex), year, int(cn_code)))["tx_hash"]


def submit_attempt(ai_result: Dict[str, Any]) -> Dict[str, Any]:
    """Seals one attempt: plant signs its declaration, the stored AI signature goes along."""
    reg = registry()
    file_key = ai_result["file_key"]
    doc_hashes = [e["doc_sha256"] for e in ai_result["extractions"]]
    nonce = reg.functions.getFile(_b32(file_key)).call()[4]
    _, plant_sig = sign_plant_declaration({
        "fileKey": file_key,
        "docsRoot": ai_result["docs_root"],
        "declarationHash": ai_result["declaration_hash"],
        "nonce": nonce,
    })
    att = ai_result["attestation"]
    att_tuple = (
        _b32(att["fileKey"]), _b32(att["inputHash"]), _b32(att["modelHash"]), _b32(att["rulesetHash"]),
        _b32(att["resultHash"]), att["status"], att["redCount"], att["yellowCount"], att["missingCount"],
        att["confidenceBps"],
    )
    sent = _send(reg.functions.submitAttempt(
        _b32(file_key), [_b32(h) for h in doc_hashes], _b32(ai_result["declaration_hash"]),
        att_tuple, _sig(plant_sig), _sig(ai_result["signature"]["sig"]),
    ))
    index = reg.events.AttemptSubmitted().process_receipt(sent["receipt"])[0]["args"]["index"]
    return {"tx_hash": sent["tx_hash"], "chain_attempt_index": int(index)}


def _sig(sig_hex: str) -> bytes:
    return bytes.fromhex(sig_hex.removeprefix("0x"))


def issue_passport(
    file_key: str,
    attempt_index: int,
    doc_hashes: List[str],
    msg: Dict[str, Any],
    verifier_sig: str,
    emissions_proof: List[int],
    scrap_proof: List[int],
) -> Dict[str, Any]:
    reg = registry()
    v_tuple = (
        _b32(msg["fileKey"]), msg["attemptIndex"], _b32(msg["docsRoot"]), _b32(msg["resultHash"]),
        _b32(msg["resolutionsHash"]), msg["redResolved"], msg["yellowChecked"], int(msg["emissionsCommitment"]),
        int(msg["scrapCommitment"]), msg["emissionsLimit"], msg["minScrapShare"], _b32(msg["vcHash"]),
    )
    sent = _send(reg.functions.issuePassport(
        _b32(file_key), attempt_index, [_b32(h) for h in doc_hashes], v_tuple, _sig(verifier_sig),
        emissions_proof, scrap_proof,
    ))
    passport_id = reg.events.PassportIssued().process_receipt(sent["receipt"])[0]["args"]["passportId"]
    return {"tx_hash": sent["tx_hash"], "passport_id": int(passport_id)}
