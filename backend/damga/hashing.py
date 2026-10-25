import hashlib
import json
from typing import Any, List, Union
import eth_abi
from eth_utils import keccak


def clean_hex(val: str) -> str:
    """Removes 0x prefix if present and returns clean 64-char hex string, filtering invalid characters."""
    val = val.strip()
    if val.startswith("0x") or val.startswith("0X"):
        val = val[2:]
    cleaned = "".join(c for c in val if c in "0123456789abcdefABCDEF")
    return cleaned.rjust(64, "0") if cleaned else "0" * 64


def canonical_json(obj: Any) -> bytes:
    """Serializes an object into canonical JSON bytes as defined in spec section 3."""
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def sha256_bytes32(data: bytes) -> str:
    """Returns SHA-256 hash formatted as 0x-prefixed 64-char hex string."""
    return "0x" + hashlib.sha256(data).hexdigest()


def keccak256_bytes(data: bytes) -> bytes:
    """Computes keccak256 returning 32 raw bytes."""
    return keccak(data)


def keccak256_hex(data: bytes) -> str:
    """Computes keccak256 returning 0x-prefixed 64-char hex string."""
    return "0x" + keccak(data).hex()


def compute_plant_id(plant_id_str: str) -> str:
    """plantId = keccak256(utf8(plant.plant_id)) -> bytes32 hex."""
    return keccak256_hex(plant_id_str.encode("utf-8"))


def compute_file_key(plant_id_hex: str, year: int, cn_code: Union[int, str]) -> str:
    """fileKey = keccak256(abi.encode(bytes32 plantId, uint16 year, uint32 cnCode))."""
    plant_bytes = bytes.fromhex(clean_hex(plant_id_hex).rjust(64, "0"))
    cn_code_int = int(cn_code)
    encoded = eth_abi.encode(["bytes32", "uint16", "uint32"], [plant_bytes, int(year), cn_code_int])
    return keccak256_hex(encoded)


def compute_doc_hash(file_bytes: bytes) -> str:
    """Document hash = SHA-256 of raw file bytes as bytes32 hex."""
    return sha256_bytes32(file_bytes)


def compute_declaration_hash(declaration_dict: dict) -> str:
    """declarationHash = SHA-256 of canonical JSON of declaration.json."""
    return sha256_bytes32(canonical_json(declaration_dict))


def compute_result_hash(ai_result_dict: dict) -> str:
    """resultHash = SHA-256 of canonical JSON of AI result without its signature field (with result_hash zeroed out to avoid circularity)."""
    import copy
    copied = copy.deepcopy(ai_result_dict)
    copied.pop("signature", None)
    copied.pop("tx_hash", None)
    copied.pop("etherscan", None)
    # The same signed result can be submitted as any attempt of its file.
    copied.pop("attempt_index", None)
    copied.pop("chain_attempt_index", None)
    copied["result_hash"] = ""
    if "attestation" in copied and isinstance(copied["attestation"], dict):
        copied["attestation"]["resultHash"] = ""
    return sha256_bytes32(canonical_json(copied))


def compute_vc_hash(vc_dict: dict) -> str:
    """vcHash = SHA-256 of canonical JSON of Verifiable Credential."""
    return sha256_bytes32(canonical_json(vc_dict))


def compute_resolutions_hash(resolutions: Any) -> str:
    """resolutionsHash = SHA-256 of canonical JSON of resolutions dict or string."""
    if resolutions is None:
        return "0x" + "00" * 32
    return sha256_bytes32(canonical_json(resolutions))


def compute_docs_root(doc_hashes: List[str]) -> str:
    """
    Merkle root over document hashes:
    leaf = keccak256(abi.encodePacked(docHash)) (where docHash is bytes32),
    leaves sorted ascending,
    parent = keccak256(sorted pair) (OpenZeppelin MerkleProof style, odd leaf carried up unchanged).
    """
    if not doc_hashes:
        return "0x" + "00" * 32

    # leaf = keccak256(docHash_bytes)
    leaves = [keccak256_bytes(bytes.fromhex(clean_hex(h).rjust(64, "0"))) for h in doc_hashes]
    leaves.sort()

    layer = leaves
    while len(layer) > 1:
        next_layer = []
        for i in range(0, len(layer), 2):
            if i + 1 < len(layer):
                a, b = layer[i], layer[i + 1]
                if a > b:
                    a, b = b, a
                next_layer.append(keccak256_bytes(a + b))
            else:
                next_layer.append(layer[i])
        layer = next_layer

    return "0x" + layer[0].hex()


def compute_input_hash(docs_root_hex: str, declaration_hash_hex: str) -> str:
    """inputHash = keccak256(abi.encode(docsRoot, declarationHash))."""
    docs_root_bytes = bytes.fromhex(clean_hex(docs_root_hex).rjust(64, "0"))
    decl_hash_bytes = bytes.fromhex(clean_hex(declaration_hash_hex).rjust(64, "0"))
    encoded = eth_abi.encode(["bytes32", "bytes32"], [docs_root_bytes, decl_hash_bytes])
    return keccak256_hex(encoded)


def compute_model_hash(provider: str, model_name: str, model_version: str) -> str:
    """modelHash = keccak256(utf8("<provider>:<model name>:<model version>"))."""
    payload = f"{provider}:{model_name}:{model_version}".encode("utf-8")
    return keccak256_hex(payload)


def compute_ruleset_hash(yaml_bytes: bytes) -> str:
    """rulesetHash = SHA-256 of the raw bytes of sectors/steel_eaf.yaml."""
    return sha256_bytes32(yaml_bytes)
