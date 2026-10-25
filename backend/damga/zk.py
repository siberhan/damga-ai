import json
import os
from pathlib import Path
import subprocess
from typing import Any, Dict, List, Optional, Tuple


def get_zk_dir() -> Path:
    backend_dir = Path(__file__).resolve().parent.parent
    return backend_dir.parent / "zk"


def compute_poseidon_commitment(value: int, salt: int) -> str:
    """
    Computes Poseidon commitment via node zk/scripts/commit.js <value> <salt>.
    Returns decimal string of field element.
    """
    zk_dir = get_zk_dir()
    commit_script = zk_dir / "scripts" / "commit.js"

    # No fallback: a commitment that is not Poseidon would not match the circuit.
    proc = subprocess.run(
        ["node", str(commit_script), str(value), str(salt)],
        cwd=str(zk_dir),
        capture_output=True,
        text=True,
        check=True,
        timeout=15,
    )
    return proc.stdout.strip()


def generate_proof(
    circuit_name: str,
    inputs: Dict[str, Any],
    out_dir: Optional[Path] = None,
) -> Tuple[Dict[str, Any], List[str], List[int]]:
    """
    Runs node zk/scripts/prove.js <circuit> <input.json> <outdir>.
    Returns (proof_dict, public_signals, uint256_8_array).
    """
    zk_dir = get_zk_dir()
    prove_script = zk_dir / "scripts" / "prove.js"

    if out_dir is None:
        out_dir = Path(__file__).resolve().parent.parent / "state" / "zk" / circuit_name
    out_dir.mkdir(parents=True, exist_ok=True)

    input_file = out_dir / "input.json"
    input_file.write_text(json.dumps(inputs, indent=2))

    # No mock fallback: if the statement is false (e.g. value > limit) the prover fails,
    # and that failure must stop the passport.
    for stale in ("proof.json", "public.json"):
        (out_dir / stale).unlink(missing_ok=True)
    try:
        proc = subprocess.run(
            ["node", str(prove_script), circuit_name, str(input_file), str(out_dir)],
            cwd=str(zk_dir),
            capture_output=True,
            text=True,
            check=True,
            timeout=30,
        )

        proof_path = out_dir / "proof.json"
        public_path = out_dir / "public.json"

        proof = json.loads(proof_path.read_text())
        public_signals = json.loads(public_path.read_text())

        # Construct uint256[8] proof array
        # pi_a[0..1], pi_b[0][0..1], pi_b[1][0..1], pi_c[0..1]
        pi_a = [int(x, 0) if isinstance(x, str) and x.startswith("0x") else int(x) for x in proof["pi_a"][:2]]
        pi_b_0 = [int(x, 0) if isinstance(x, str) and x.startswith("0x") else int(x) for x in proof["pi_b"][0][:2]]
        pi_b_1 = [int(x, 0) if isinstance(x, str) and x.startswith("0x") else int(x) for x in proof["pi_b"][1][:2]]
        pi_c = [int(x, 0) if isinstance(x, str) and x.startswith("0x") else int(x) for x in proof["pi_c"][:2]]

        # snarkjs' Solidity verifier takes each G2 coordinate pair in reversed order.
        u8_proof = [
            pi_a[0], pi_a[1],
            pi_b_0[1], pi_b_0[0],
            pi_b_1[1], pi_b_1[0],
            pi_c[0], pi_c[1],
        ]

        return proof, public_signals, u8_proof

    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"ZK proof failed for {circuit_name}: the claim does not hold or inputs are invalid") from e


def verify_zk_proof(circuit_name: str, proof_path: Path, public_path: Path) -> bool:
    """Verifies proof using node zk/scripts/verify.js."""
    zk_dir = get_zk_dir()
    verify_script = zk_dir / "scripts" / "verify.js"

    if not verify_script.exists():
        return False

    try:
        proc = subprocess.run(
            ["node", str(verify_script), circuit_name, str(proof_path), str(public_path)],
            cwd=str(zk_dir),
            capture_output=True,
            text=True,
            check=True,
            timeout=15,
        )
        return "PASS" in proc.stdout
    except Exception:
        return False
