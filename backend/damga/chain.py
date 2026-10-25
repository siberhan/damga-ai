import json
import os
from pathlib import Path
from typing import Any, Dict, Optional, Tuple
from eth_account import Account
from eth_account.messages import encode_typed_data
from web3 import Web3


def get_project_root() -> Path:
    backend_dir = Path(__file__).resolve().parent.parent
    return backend_dir.parent


def get_registry_address() -> str:
    addr = os.environ.get("DAMGA_REGISTRY_ADDRESS", "").strip()
    return addr


def is_offline() -> bool:
    return not bool(get_registry_address())


def get_contract_abi() -> list:
    root = get_project_root()
    real_abi_path = root / "contracts" / "abi" / "DamgaRegistry.json"
    if real_abi_path.exists():
        data = json.loads(real_abi_path.read_text())
        if isinstance(data, dict) and "abi" in data:
            return data["abi"]
        return data

    fallback_path = Path(__file__).resolve().parent / "abi_fallback.json"
    return json.loads(fallback_path.read_text())


def get_eip712_domain(verifying_contract: Optional[str] = None) -> Dict[str, Any]:
    registry = verifying_contract or get_registry_address()
    if not registry or not Web3.is_address(registry):
        registry = "0x0000000000000000000000000000000000000000"
    else:
        registry = Web3.to_checksum_address(registry)

    return {
        "name": "DamgaAI",
        "version": "1",
        "chainId": 11155111,
        "verifyingContract": registry,
    }


def get_typed_data_payload(primary_type: str, message: Dict[str, Any], verifying_contract: Optional[str] = None) -> Dict[str, Any]:
    domain = get_eip712_domain(verifying_contract)
    all_structs = {
        "PlantDeclaration": [
            {"name": "fileKey", "type": "bytes32"},
            {"name": "docsRoot", "type": "bytes32"},
            {"name": "declarationHash", "type": "bytes32"},
            {"name": "nonce", "type": "uint256"},
        ],
        "AIAttestation": [
            {"name": "fileKey", "type": "bytes32"},
            {"name": "inputHash", "type": "bytes32"},
            {"name": "modelHash", "type": "bytes32"},
            {"name": "rulesetHash", "type": "bytes32"},
            {"name": "resultHash", "type": "bytes32"},
            {"name": "status", "type": "uint8"},
            {"name": "redCount", "type": "uint16"},
            {"name": "yellowCount", "type": "uint16"},
            {"name": "missingCount", "type": "uint16"},
            {"name": "confidenceBps", "type": "uint16"},
        ],
        "Verification": [
            {"name": "fileKey", "type": "bytes32"},
            {"name": "attemptIndex", "type": "uint256"},
            {"name": "docsRoot", "type": "bytes32"},
            {"name": "resultHash", "type": "bytes32"},
            {"name": "resolutionsHash", "type": "bytes32"},
            {"name": "redResolved", "type": "uint16"},
            {"name": "yellowChecked", "type": "uint16"},
            {"name": "emissionsCommitment", "type": "uint256"},
            {"name": "scrapCommitment", "type": "uint256"},
            {"name": "emissionsLimit", "type": "uint32"},
            {"name": "minScrapShare", "type": "uint16"},
            {"name": "vcHash", "type": "bytes32"},
        ],
    }

    types = {
        "EIP712Domain": [
            {"name": "name", "type": "string"},
            {"name": "version", "type": "string"},
            {"name": "chainId", "type": "uint256"},
            {"name": "verifyingContract", "type": "address"},
        ],
    }

    if primary_type in all_structs:
        types[primary_type] = all_structs[primary_type]
    else:
        types.update(all_structs)

    return {
        "types": types,
        "domain": domain,
        "primaryType": primary_type,
        "message": message,
    }


def _get_key_or_fallback(env_var: str, fallback_seed: str) -> str:
    key = os.environ.get(env_var, "").strip()
    if key:
        return key if key.startswith("0x") else f"0x{key}"
    # Deterministic fallback key for offline demos/tests
    import hashlib
    seed_hash = hashlib.sha256(fallback_seed.encode()).hexdigest()
    return f"0x{seed_hash}"


def sign_ai_attestation(attestation: Dict[str, Any], private_key: Optional[str] = None) -> Tuple[str, str]:
    """Signs AIAttestation returning (signer_address, signature_hex)."""
    key = private_key or _get_key_or_fallback("AI_SIGNER_PRIVATE_KEY", "damga_ai_signer_demo_key_2026")
    acct = Account.from_key(key)
    structured_data = get_typed_data_payload("AIAttestation", attestation)
    signable = encode_typed_data(full_message=structured_data)
    signed = Account.sign_message(signable, key)
    sig_hex = signed.signature.hex()
    if not sig_hex.startswith("0x"):
        sig_hex = "0x" + sig_hex
    return acct.address, sig_hex


def sign_plant_declaration(declaration_msg: Dict[str, Any], private_key: Optional[str] = None) -> Tuple[str, str]:
    """Signs PlantDeclaration returning (signer_address, signature_hex)."""
    key = private_key or _get_key_or_fallback("PLANT_SIGNER_PRIVATE_KEY", "damga_plant_signer_demo_key_2026")
    acct = Account.from_key(key)
    structured_data = get_typed_data_payload("PlantDeclaration", declaration_msg)
    signable = encode_typed_data(full_message=structured_data)
    signed = Account.sign_message(signable, key)
    sig_hex = signed.signature.hex()
    if not sig_hex.startswith("0x"):
        sig_hex = "0x" + sig_hex
    return acct.address, sig_hex


def sign_verification(verification_msg: Dict[str, Any], private_key: Optional[str] = None) -> Tuple[str, str]:
    """Signs Verification returning (signer_address, signature_hex)."""
    key = private_key or _get_key_or_fallback("DEMO_VERIFIER_PRIVATE_KEY", "damga_demo_verifier_demo_key_2026")
    acct = Account.from_key(key)
    structured_data = get_typed_data_payload("Verification", verification_msg)
    signable = encode_typed_data(full_message=structured_data)
    signed = Account.sign_message(signable, key)
    sig_hex = signed.signature.hex()
    if not sig_hex.startswith("0x"):
        sig_hex = "0x" + sig_hex
    return acct.address, sig_hex


def recover_typed_signer(primary_type: str, message: Dict[str, Any], signature: str, verifying_contract: Optional[str] = None) -> str:
    """Recovers the signer address from an EIP-712 signature."""
    structured_data = get_typed_data_payload(primary_type, message, verifying_contract)
    signable = encode_typed_data(full_message=structured_data)
    recovered = Account.recover_message(signable, signature=signature)
    return recovered


def get_web3_client() -> Optional[Web3]:
    rpc = os.environ.get("SEPOLIA_RPC_URL", "https://ethereum-sepolia-rpc.publicnode.com").strip()
    if not rpc:
        return None
    try:
        w3 = Web3(Web3.HTTPProvider(rpc, request_kwargs={"timeout": 15}))
        return w3
    except Exception:
        return None
