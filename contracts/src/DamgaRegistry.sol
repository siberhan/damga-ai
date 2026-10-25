// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import {EIP712} from "@openzeppelin/contracts/utils/cryptography/EIP712.sol";
import {ECDSA} from "@openzeppelin/contracts/utils/cryptography/ECDSA.sol";
import {Ownable} from "@openzeppelin/contracts/access/Ownable.sol";
import {IGroth16Verifier} from "./interfaces/IGroth16Verifier.sol";

/**
 * @title DamgaRegistry
 * @notice Central registry for Turkish scrap EAF steel CBAM export declarations,
 *         audit attempts, Groth16 zero-knowledge proofs, and verifiable digital product passports.
 */
contract DamgaRegistry is EIP712, Ownable {
    using ECDSA for bytes32;

    // --- Custom Errors ---
    error DocsChanged();
    error DocReused();
    error PassportExists();
    error NotLatestAttempt();
    error BadSignature();
    error UnapprovedModel();
    error UnapprovedRuleset();
    error OpenRedFlags();
    error UncheckedYellowFlags();
    error MissingEvidence();
    error InvalidProof();
    error InputHashMismatch();
    error ResultHashMismatch();
    error Unauthorized();
    error PassportNotFound();
    error FileNotFound();
    error PassportNotActive();

    // --- Enums and Structs ---
    enum PassportStatus {
        NONE,
        ACTIVE,
        REVOKED,
        DISPUTED,
        SUPERSEDED
    }

    struct VerifierInfo {
        bool active;
        string name;
    }

    struct PlantDeclaration {
        bytes32 fileKey;
        bytes32 docsRoot;
        bytes32 declarationHash;
        uint256 nonce;
    }

    struct AIAttestation {
        bytes32 fileKey;
        bytes32 inputHash;
        bytes32 modelHash;
        bytes32 rulesetHash;
        bytes32 resultHash;
        uint8 status;
        uint16 redCount;
        uint16 yellowCount;
        uint16 missingCount;
        uint16 confidenceBps;
    }

    struct Verification {
        bytes32 fileKey;
        uint256 attemptIndex;
        bytes32 docsRoot;
        bytes32 resultHash;
        bytes32 resolutionsHash;
        uint16 redResolved;
        uint16 yellowChecked;
        uint256 emissionsCommitment;
        uint256 scrapCommitment;
        uint32 emissionsLimit;
        uint16 minScrapShare;
        bytes32 vcHash;
    }

    struct FileRecord {
        bytes32 plantId;
        uint16 year;
        uint32 cnCode;
        uint256 activePassportId;
        uint256 nonce;
        bool registered;
    }

    struct Attempt {
        bytes32 docsRoot;
        bytes32 declarationHash;
        bytes32 inputHash;
        bytes32 modelHash;
        bytes32 rulesetHash;
        bytes32 resultHash;
        uint8 status;
        uint16 redCount;
        uint16 yellowCount;
        uint16 missingCount;
        uint16 confidenceBps;
        uint256 timestamp;
    }

    struct Passport {
        bytes32 fileKey;
        uint256 attemptIndex;
        uint256 version;
        uint256 prevPassportId;
        address verifier;
        bytes32 docsRoot;
        bytes32 resultHash;
        uint256 emissionsCommitment;
        uint256 scrapCommitment;
        uint32 emissionsLimit;
        uint16 minScrapShare;
        bytes32 modelHash;
        bytes32 rulesetHash;
        bytes32 vcHash;
        PassportStatus status;
        uint256 issuedAt;
    }

    // --- EIP-712 TypeHashes ---
    bytes32 public constant PLANT_DECLARATION_TYPEHASH = keccak256(
        "PlantDeclaration(bytes32 fileKey,bytes32 docsRoot,bytes32 declarationHash,uint256 nonce)"
    );

    bytes32 public constant AI_ATTESTATION_TYPEHASH = keccak256(
        "AIAttestation(bytes32 fileKey,bytes32 inputHash,bytes32 modelHash,bytes32 rulesetHash,bytes32 resultHash,uint8 status,uint16 redCount,uint16 yellowCount,uint16 missingCount,uint16 confidenceBps)"
    );

    bytes32 public constant VERIFICATION_TYPEHASH = keccak256(
        "Verification(bytes32 fileKey,uint256 attemptIndex,bytes32 docsRoot,bytes32 resultHash,bytes32 resolutionsHash,uint16 redResolved,uint16 yellowChecked,uint256 emissionsCommitment,uint256 scrapCommitment,uint32 emissionsLimit,uint16 minScrapShare,bytes32 vcHash)"
    );

    // --- State Variables ---
    IGroth16Verifier public immutable emissionsVerifier;
    IGroth16Verifier public immutable scrapVerifier;

    mapping(address => bool) public aiSigners;
    mapping(address => VerifierInfo) public verifiers;
    mapping(bytes32 => address) public plantSigners;
    mapping(bytes32 => bool) public approvedModels;
    mapping(bytes32 => bool) public approvedRulesets;

    mapping(bytes32 => FileRecord) internal _files;
    mapping(bytes32 => Attempt[]) internal _fileAttempts;
    mapping(bytes32 => bytes32) public docToFileKey;
    mapping(uint256 => Passport) internal _passports;
    mapping(bytes32 => uint256) public passportOfFile;

    uint256 public totalPassports;

    // --- Events ---
    event FileRegistered(bytes32 indexed fileKey, bytes32 indexed plantId, uint16 year, uint32 cnCode);
    event AttemptSubmitted(
        bytes32 indexed fileKey,
        uint256 indexed index,
        uint8 status,
        uint16 redCount,
        uint16 yellowCount,
        uint16 missingCount,
        bytes32 resultHash
    );
    event PassportIssued(
        uint256 indexed passportId,
        bytes32 indexed fileKey,
        uint256 indexed attemptIndex,
        address verifier
    );
    event PassportRevoked(uint256 indexed passportId, bytes32 reasonHash, bool supersede);
    event PassportDisputed(uint256 indexed passportId, bytes32 reasonHash);

    event AISignerUpdated(address indexed signer, bool active);
    event VerifierUpdated(address indexed verifier, bool active, string name);
    event PlantSignerUpdated(bytes32 indexed plantId, address indexed signer);
    event ModelApproved(bytes32 indexed modelHash, bool approved);
    event RulesetApproved(bytes32 indexed rulesetHash, bool approved);

    constructor(address _emissionsVerifier, address _scrapVerifier)
        EIP712("DamgaAI", "1")
        Ownable(msg.sender)
    {
        emissionsVerifier = IGroth16Verifier(_emissionsVerifier);
        scrapVerifier = IGroth16Verifier(_scrapVerifier);
    }

    // --- Role Management (Owner Only) ---
    function setAISigner(address signer, bool active) external onlyOwner {
        aiSigners[signer] = active;
        emit AISignerUpdated(signer, active);
    }

    function setVerifier(address verifier, bool active, string calldata name) external onlyOwner {
        verifiers[verifier] = VerifierInfo({active: active, name: name});
        emit VerifierUpdated(verifier, active, name);
    }

    function setPlantSigner(bytes32 plantId, address signer) external onlyOwner {
        plantSigners[plantId] = signer;
        emit PlantSignerUpdated(plantId, signer);
    }

    function setApprovedModel(bytes32 modelHash, bool approved) external onlyOwner {
        approvedModels[modelHash] = approved;
        emit ModelApproved(modelHash, approved);
    }

    function setApprovedRuleset(bytes32 rulesetHash, bool approved) external onlyOwner {
        approvedRulesets[rulesetHash] = approved;
        emit RulesetApproved(rulesetHash, approved);
    }

    // --- Merkle Root Calculation ---
    /**
     * @notice Recomputes docsRoot from docHashes.
     * leaf = keccak256(abi.encodePacked(docHash)), leaves sorted ascending,
     * parent = keccak256(sorted pair) (OZ MerkleProof style, odd leaf carried up unchanged).
     */
    function computeDocsRoot(bytes32[] memory docHashes) public pure returns (bytes32) {
        uint256 n = docHashes.length;
        if (n == 0) return bytes32(0);

        bytes32[] memory layer = new bytes32[](n);
        for (uint256 i = 0; i < n; i++) {
            layer[i] = keccak256(abi.encodePacked(docHashes[i]));
        }

        // Sort leaves ascending (insertion sort)
        for (uint256 i = 1; i < n; i++) {
            bytes32 key = layer[i];
            uint256 j = i;
            while (j > 0 && uint256(layer[j - 1]) > uint256(key)) {
                layer[j] = layer[j - 1];
                j--;
            }
            layer[j] = key;
        }

        // Tree reduction
        uint256 currentLen = n;
        while (currentLen > 1) {
            uint256 nextLen = (currentLen + 1) / 2;
            for (uint256 i = 0; i < currentLen / 2; i++) {
                bytes32 a = layer[2 * i];
                bytes32 b = layer[2 * i + 1];
                if (uint256(a) > uint256(b)) {
                    (a, b) = (b, a);
                }
                layer[i] = keccak256(abi.encodePacked(a, b));
            }
            if (currentLen % 2 == 1) {
                layer[nextLen - 1] = layer[currentLen - 1];
            }
            currentLen = nextLen;
        }

        return layer[0];
    }

    // --- Core Protocol Functions ---

    /**
     * @notice Registers a new CBAM file for a given plant, year, and CN code.
     * @param plantId keccak256(utf8(plant.plant_id))
     * @param year Reporting year (e.g. 2026)
     * @param cnCode 8-digit CN code as uint32
     * @return fileKey keccak256(abi.encode(plantId, year, cnCode))
     */
    function registerFile(bytes32 plantId, uint16 year, uint32 cnCode) external returns (bytes32 fileKey) {
        fileKey = keccak256(abi.encode(plantId, year, cnCode));
        if (!_files[fileKey].registered) {
            _files[fileKey] = FileRecord({
                plantId: plantId,
                year: year,
                cnCode: cnCode,
                activePassportId: 0,
                nonce: 0,
                registered: true
            });
            emit FileRegistered(fileKey, plantId, year, cnCode);
        }
    }

    /**
     * @notice Submits an audit attempt for a registered file.
     * @param fileKey The identifier of the file
     * @param docHashes SHA-256 hashes of all evidence documents
     * @param declarationHash SHA-256 of canonical declaration.json
     * @param att AI attestation struct
     * @param plantSig EIP-712 signature from plant signer
     * @param aiSig EIP-712 signature from registered AI signer
     * @return attemptIndex Index of newly stored attempt
     */
    function submitAttempt(
        bytes32 fileKey,
        bytes32[] calldata docHashes,
        bytes32 declarationHash,
        AIAttestation calldata att,
        bytes calldata plantSig,
        bytes calldata aiSig
    ) external returns (uint256 attemptIndex) {
        FileRecord storage file = _files[fileKey];
        if (!file.registered) revert FileNotFound();

        // 1. Recompute docsRoot
        bytes32 docsRoot = computeDocsRoot(docHashes);

        // 2. Check each doc hash not used by another fileKey (DocReused)
        for (uint256 i = 0; i < docHashes.length; i++) {
            bytes32 docHash = docHashes[i];
            bytes32 existingFileKey = docToFileKey[docHash];
            if (existingFileKey != bytes32(0) && existingFileKey != fileKey) {
                revert DocReused();
            }
            docToFileKey[docHash] = fileKey;
        }

        // 3. Verify Plant signature
        bytes32 plantStructHash = keccak256(
            abi.encode(
                PLANT_DECLARATION_TYPEHASH,
                fileKey,
                docsRoot,
                declarationHash,
                file.nonce
            )
        );
        bytes32 plantDigest = _hashTypedDataV4(plantStructHash);
        address plantSigner = ECDSA.recover(plantDigest, plantSig);
        address expectedPlantSigner = plantSigners[file.plantId];
        if (expectedPlantSigner == address(0) || plantSigner != expectedPlantSigner) {
            revert BadSignature();
        }
        file.nonce++;

        // 4. Verify AI signature
        if (att.fileKey != fileKey) revert BadSignature();
        bytes32 aiStructHash = keccak256(
            abi.encode(
                AI_ATTESTATION_TYPEHASH,
                att.fileKey,
                att.inputHash,
                att.modelHash,
                att.rulesetHash,
                att.resultHash,
                att.status,
                att.redCount,
                att.yellowCount,
                att.missingCount,
                att.confidenceBps
            )
        );
        bytes32 aiDigest = _hashTypedDataV4(aiStructHash);
        address aiSigner = ECDSA.recover(aiDigest, aiSig);
        if (!aiSigners[aiSigner] || aiSigner == address(0)) {
            revert BadSignature();
        }

        // 5. Verify inputHash
        bytes32 expectedInputHash = keccak256(abi.encode(docsRoot, declarationHash));
        if (att.inputHash != expectedInputHash) {
            revert InputHashMismatch();
        }

        // 6. Verify approved model and ruleset
        if (!approvedModels[att.modelHash]) {
            revert UnapprovedModel();
        }
        if (!approvedRulesets[att.rulesetHash]) {
            revert UnapprovedRuleset();
        }

        // 7. Store attempt
        attemptIndex = _fileAttempts[fileKey].length;
        _fileAttempts[fileKey].push(
            Attempt({
                docsRoot: docsRoot,
                declarationHash: declarationHash,
                inputHash: att.inputHash,
                modelHash: att.modelHash,
                rulesetHash: att.rulesetHash,
                resultHash: att.resultHash,
                status: att.status,
                redCount: att.redCount,
                yellowCount: att.yellowCount,
                missingCount: att.missingCount,
                confidenceBps: att.confidenceBps,
                timestamp: block.timestamp
            })
        );

        emit AttemptSubmitted(
            fileKey,
            attemptIndex,
            att.status,
            att.redCount,
            att.yellowCount,
            att.missingCount,
            att.resultHash
        );
    }

    /**
     * @notice Issues a verifiable digital product passport after verifier audit and ZK verification.
     * @param fileKey The identifier of the file
     * @param attemptIndex Index of attempt to certify (must be latest)
     * @param docHashes Hashes of all evidence documents (must match sealed docsRoot)
     * @param v Verification details signed by verifier
     * @param verifierSig EIP-712 signature from accredited verifier
     * @param emissionsProof Groth16 proof [a0,a1,b00,b01,b10,b11,c0,c1] for direct emissions <= limit
     * @param scrapProof Groth16 proof [a0,a1,b00,b01,b10,b11,c0,c1] for scrap share >= minShare
     * @return passportId Unique identifier of minted passport
     */
    function issuePassport(
        bytes32 fileKey,
        uint256 attemptIndex,
        bytes32[] calldata docHashes,
        Verification calldata v,
        bytes calldata verifierSig,
        uint256[8] calldata emissionsProof,
        uint256[8] calldata scrapProof
    ) external returns (uint256 passportId) {
        FileRecord storage file = _files[fileKey];
        if (!file.registered) revert FileNotFound();

        // 1. Attempt must be latest of file
        Attempt[] storage attempts = _fileAttempts[fileKey];
        if (attempts.length == 0 || attemptIndex != attempts.length - 1) {
            revert NotLatestAttempt();
        }
        Attempt storage att = attempts[attemptIndex];

        // 2. Docs unchanged check
        bytes32 docsRoot = computeDocsRoot(docHashes);
        if (docsRoot != att.docsRoot) {
            revert DocsChanged();
        }

        // 3. Verification struct matching
        if (v.fileKey != fileKey || v.attemptIndex != attemptIndex || v.docsRoot != att.docsRoot) {
            revert BadSignature();
        }
        if (v.resultHash != att.resultHash) {
            revert ResultHashMismatch();
        }

        // 4. Verifier signature check
        bytes32 vStructHash = keccak256(
            abi.encode(
                VERIFICATION_TYPEHASH,
                v.fileKey,
                v.attemptIndex,
                v.docsRoot,
                v.resultHash,
                v.resolutionsHash,
                v.redResolved,
                v.yellowChecked,
                v.emissionsCommitment,
                v.scrapCommitment,
                v.emissionsLimit,
                v.minScrapShare,
                v.vcHash
            )
        );
        bytes32 vDigest = _hashTypedDataV4(vStructHash);
        address verifier = ECDSA.recover(vDigest, verifierSig);
        if (!verifiers[verifier].active || verifier == address(0)) {
            revert BadSignature();
        }

        // 5. Status & flag checks: MISSING (status 3 or missingCount > 0) always blocks
        if (att.status == 3 || att.missingCount > 0) {
            revert MissingEvidence();
        }
        if (v.redResolved != att.redCount) {
            revert OpenRedFlags();
        }
        if (v.yellowChecked != att.yellowCount) {
            revert UncheckedYellowFlags();
        }

        // 6. Passport active / supersede checks
        uint256 currentPassportId = passportOfFile[fileKey];
        uint256 version = 1;
        uint256 prevPassportId = 0;
        if (currentPassportId != 0) {
            Passport storage current = _passports[currentPassportId];
            if (current.status == PassportStatus.ACTIVE) {
                revert PassportExists();
            } else if (current.status == PassportStatus.SUPERSEDED) {
                version = current.version + 1;
                prevPassportId = currentPassportId;
            } else {
                revert PassportExists();
            }
        }

        // 7. Verify Groth16 proofs
        // Emissions proof
        uint256[2] memory pA_em = [emissionsProof[0], emissionsProof[1]];
        uint256[2][2] memory pB_em = [
            [emissionsProof[2], emissionsProof[3]],
            [emissionsProof[4], emissionsProof[5]]
        ];
        uint256[2] memory pC_em = [emissionsProof[6], emissionsProof[7]];
        uint256[2] memory pub_em = [v.emissionsCommitment, uint256(v.emissionsLimit)];

        if (!emissionsVerifier.verifyProof(pA_em, pB_em, pC_em, pub_em)) {
            revert InvalidProof();
        }

        // Scrap proof
        uint256[2] memory pA_sc = [scrapProof[0], scrapProof[1]];
        uint256[2][2] memory pB_sc = [
            [scrapProof[2], scrapProof[3]],
            [scrapProof[4], scrapProof[5]]
        ];
        uint256[2] memory pC_sc = [scrapProof[6], scrapProof[7]];
        uint256[2] memory pub_sc = [v.scrapCommitment, uint256(v.minScrapShare)];

        if (!scrapVerifier.verifyProof(pA_sc, pB_sc, pC_sc, pub_sc)) {
            revert InvalidProof();
        }

        // 8. Mint passport
        passportId = ++totalPassports;
        _passports[passportId] = Passport({
            fileKey: fileKey,
            attemptIndex: attemptIndex,
            version: version,
            prevPassportId: prevPassportId,
            verifier: verifier,
            docsRoot: att.docsRoot,
            resultHash: att.resultHash,
            emissionsCommitment: v.emissionsCommitment,
            scrapCommitment: v.scrapCommitment,
            emissionsLimit: v.emissionsLimit,
            minScrapShare: v.minScrapShare,
            modelHash: att.modelHash,
            rulesetHash: att.rulesetHash,
            vcHash: v.vcHash,
            status: PassportStatus.ACTIVE,
            issuedAt: block.timestamp
        });

        passportOfFile[fileKey] = passportId;
        file.activePassportId = passportId;

        emit PassportIssued(passportId, fileKey, attemptIndex, verifier);
    }

    /**
     * @notice Revokes a passport. May only be called by the issuing verifier or registry owner.
     * @param passportId Passport ID to revoke
     * @param reasonHash Hash of revocation rationale
     * @param supersede If true, sets status to SUPERSEDED, allowing a new version to be issued
     */
    function revokePassport(uint256 passportId, bytes32 reasonHash, bool supersede) external {
        Passport storage p = _passports[passportId];
        if (p.issuedAt == 0) revert PassportNotFound();
        if (msg.sender != p.verifier && msg.sender != owner()) revert Unauthorized();
        if (p.status != PassportStatus.ACTIVE) revert PassportNotActive();

        if (supersede) {
            p.status = PassportStatus.SUPERSEDED;
        } else {
            p.status = PassportStatus.REVOKED;
            _files[p.fileKey].activePassportId = 0;
        }

        emit PassportRevoked(passportId, reasonHash, supersede);
    }

    /**
     * @notice Disputes a passport (e.g. by customs / importer via governance).
     * @param passportId Passport ID to dispute
     * @param reasonHash Hash of dispute evidence / rationale
     */
    function disputePassport(uint256 passportId, bytes32 reasonHash) external onlyOwner {
        Passport storage p = _passports[passportId];
        if (p.issuedAt == 0) revert PassportNotFound();
        if (p.status != PassportStatus.ACTIVE) revert PassportNotActive();

        p.status = PassportStatus.DISPUTED;
        _files[p.fileKey].activePassportId = 0;

        emit PassportDisputed(passportId, reasonHash);
    }

    // --- Views ---

    function getFile(bytes32 fileKey) external view returns (FileRecord memory) {
        return _files[fileKey];
    }

    function getAttempts(bytes32 fileKey) external view returns (Attempt[] memory) {
        return _fileAttempts[fileKey];
    }

    function getPassport(uint256 id) external view returns (Passport memory) {
        if (_passports[id].issuedAt == 0) revert PassportNotFound();
        return _passports[id];
    }

}
