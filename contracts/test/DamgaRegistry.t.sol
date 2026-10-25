// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import {Test} from "forge-std/Test.sol";
import {DamgaRegistry} from "../src/DamgaRegistry.sol";
import {IGroth16Verifier} from "../src/interfaces/IGroth16Verifier.sol";
import {EmissionsLeLimitVerifier} from "../src/verifiers/EmissionsLeLimitVerifier.sol";
import {ScrapShareGeVerifier} from "../src/verifiers/ScrapShareGeVerifier.sol";

contract MockGroth16Verifier is IGroth16Verifier {
    bool public shouldPass = true;

    function setShouldPass(bool _pass) external {
        shouldPass = _pass;
    }

    function verifyProof(
        uint256[2] calldata,
        uint256[2][2] calldata,
        uint256[2] calldata,
        uint256[2] calldata
    ) external view returns (bool) {
        return shouldPass;
    }
}

contract DamgaRegistryTest is Test {
    DamgaRegistry public registry;
    MockGroth16Verifier public mockEmissionsVerifier;
    MockGroth16Verifier public mockScrapVerifier;

    uint256 internal plantSignerPk = 0x1111;
    address internal plantSigner;

    uint256 internal aiSignerPk = 0x2222;
    address internal aiSigner;

    uint256 internal verifierPk = 0x3333;
    address internal verifierSigner;

    uint256 internal unauthorizedPk = 0x9999;
    address internal unauthorizedSigner;

    bytes32 internal plantId = keccak256(bytes("TR-ALIAGA-DEMO-001"));
    uint16 internal year = 2026;
    uint32 internal cnCode = 72142000;
    bytes32 internal fileKey;

    bytes32 internal modelHash = keccak256(bytes("mistral:mistral-large-latest:1.0.0"));
    bytes32 internal rulesetHash = keccak256(bytes("sectors/steel_eaf.yaml"));

    bytes32 internal declarationHash = keccak256(bytes("canonical_declaration_json"));
    bytes32[] internal sampleDocHashes;

    uint256[8] internal dummyProof = [
        uint256(1), uint256(2), uint256(3), uint256(4),
        uint256(5), uint256(6), uint256(7), uint256(8)
    ];

    function setUp() public {
        plantSigner = vm.addr(plantSignerPk);
        aiSigner = vm.addr(aiSignerPk);
        verifierSigner = vm.addr(verifierPk);
        unauthorizedSigner = vm.addr(unauthorizedPk);

        mockEmissionsVerifier = new MockGroth16Verifier();
        mockScrapVerifier = new MockGroth16Verifier();

        registry = new DamgaRegistry(
            address(mockEmissionsVerifier),
            address(mockScrapVerifier)
        );

        // Configure roles
        registry.setPlantSigner(plantId, plantSigner);
        registry.setAISigner(aiSigner, true);
        registry.setVerifier(verifierSigner, true, "Demo Verification GmbH (fictional)");
        registry.setApprovedModel(modelHash, true);
        registry.setApprovedRuleset(rulesetHash, true);

        // Prepare sample doc hashes
        sampleDocHashes = new bytes32[](3);
        sampleDocHashes[0] = keccak256(bytes("gas_bill_01"));
        sampleDocHashes[1] = keccak256(bytes("scrap_invoice_01"));
        sampleDocHashes[2] = keccak256(bytes("weighbridge_01"));

        fileKey = registry.registerFile(plantId, year, cnCode);
    }

    // --- Helper to build EIP-712 digests ---

    function _domainSeparator() internal view returns (bytes32) {
        return keccak256(
            abi.encode(
                keccak256("EIP712Domain(string name,string version,uint256 chainId,address verifyingContract)"),
                keccak256(bytes("DamgaAI")),
                keccak256(bytes("1")),
                block.chainid,
                address(registry)
            )
        );
    }

    function _signPlantDeclaration(
        uint256 pk,
        bytes32 _fileKey,
        bytes32 _docsRoot,
        bytes32 _declarationHash,
        uint256 _nonce
    ) internal view returns (bytes memory) {
        bytes32 structHash = keccak256(
            abi.encode(
                registry.PLANT_DECLARATION_TYPEHASH(),
                _fileKey,
                _docsRoot,
                _declarationHash,
                _nonce
            )
        );
        bytes32 digest = keccak256(abi.encodePacked("\x19\x01", _domainSeparator(), structHash));
        (uint8 v, bytes32 r, bytes32 s) = vm.sign(pk, digest);
        return abi.encodePacked(r, s, v);
    }

    function _signAIAttestation(
        uint256 pk,
        DamgaRegistry.AIAttestation memory att
    ) internal view returns (bytes memory) {
        bytes32 structHash = keccak256(
            abi.encode(
                registry.AI_ATTESTATION_TYPEHASH(),
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
        bytes32 digest = keccak256(abi.encodePacked("\x19\x01", _domainSeparator(), structHash));
        (uint8 v, bytes32 r, bytes32 s) = vm.sign(pk, digest);
        return abi.encodePacked(r, s, v);
    }

    function _signVerification(
        uint256 pk,
        DamgaRegistry.Verification memory vrf
    ) internal view returns (bytes memory) {
        bytes32 structHash = keccak256(
            abi.encode(
                registry.VERIFICATION_TYPEHASH(),
                vrf.fileKey,
                vrf.attemptIndex,
                vrf.docsRoot,
                vrf.resultHash,
                vrf.resolutionsHash,
                vrf.redResolved,
                vrf.yellowChecked,
                vrf.emissionsCommitment,
                vrf.scrapCommitment,
                vrf.emissionsLimit,
                vrf.minScrapShare,
                vrf.vcHash
            )
        );
        bytes32 digest = keccak256(abi.encodePacked("\x19\x01", _domainSeparator(), structHash));
        (uint8 v, bytes32 r, bytes32 s) = vm.sign(pk, digest);
        return abi.encodePacked(r, s, v);
    }

    // --- Tests ---

    function test_HappyPath() public {
        bytes32 docsRoot = registry.computeDocsRoot(sampleDocHashes);
        bytes32 inputHash = keccak256(abi.encode(docsRoot, declarationHash));
        bytes32 resultHash = keccak256(bytes("ai_result_clean_v1"));

        bytes memory plantSig = _signPlantDeclaration(
            plantSignerPk,
            fileKey,
            docsRoot,
            declarationHash,
            0
        );

        DamgaRegistry.AIAttestation memory att = DamgaRegistry.AIAttestation({
            fileKey: fileKey,
            inputHash: inputHash,
            modelHash: modelHash,
            rulesetHash: rulesetHash,
            resultHash: resultHash,
            status: 0, // GREEN
            redCount: 0,
            yellowCount: 0,
            missingCount: 0,
            confidenceBps: 9800
        });
        bytes memory aiSig = _signAIAttestation(aiSignerPk, att);

        uint256 attemptIdx = registry.submitAttempt(
            fileKey,
            sampleDocHashes,
            declarationHash,
            att,
            plantSig,
            aiSig
        );
        assertEq(attemptIdx, 0);

        DamgaRegistry.Verification memory vrf = DamgaRegistry.Verification({
            fileKey: fileKey,
            attemptIndex: 0,
            docsRoot: docsRoot,
            resultHash: resultHash,
            resolutionsHash: bytes32(0),
            redResolved: 0,
            yellowChecked: 0,
            emissionsCommitment: 123456789,
            scrapCommitment: 987654321,
            emissionsLimit: 150,
            minScrapShare: 900,
            vcHash: keccak256(bytes("vc_hash_01"))
        });
        bytes memory verifierSig = _signVerification(verifierPk, vrf);

        uint256 passportId = registry.issuePassport(
            fileKey,
            0,
            sampleDocHashes,
            vrf,
            verifierSig,
            dummyProof,
            dummyProof
        );

        assertEq(passportId, 1);
        assertEq(registry.passportOfFile(fileKey), 1);

        DamgaRegistry.Passport memory p = registry.getPassport(1);
        assertEq(p.fileKey, fileKey);
        assertEq(p.attemptIndex, 0);
        assertEq(p.version, 1);
        assertEq(p.prevPassportId, 0);
        assertEq(p.verifier, verifierSigner);
        assertEq(p.docsRoot, docsRoot);
        assertEq(p.resultHash, resultHash);
        assertEq(p.emissionsCommitment, 123456789);
        assertEq(p.scrapCommitment, 987654321);
        assertEq(p.emissionsLimit, 150);
        assertEq(p.minScrapShare, 900);
        assertEq(uint8(p.status), uint8(DamgaRegistry.PassportStatus.ACTIVE));
    }

    function test_RevertWhen_RedAttemptWithoutResolutions() public {
        bytes32 docsRoot = registry.computeDocsRoot(sampleDocHashes);
        bytes32 inputHash = keccak256(abi.encode(docsRoot, declarationHash));
        bytes32 resultHash = keccak256(bytes("ai_result_red"));

        bytes memory plantSig = _signPlantDeclaration(
            plantSignerPk,
            fileKey,
            docsRoot,
            declarationHash,
            0
        );

        DamgaRegistry.AIAttestation memory att = DamgaRegistry.AIAttestation({
            fileKey: fileKey,
            inputHash: inputHash,
            modelHash: modelHash,
            rulesetHash: rulesetHash,
            resultHash: resultHash,
            status: 2, // RED
            redCount: 2,
            yellowCount: 0,
            missingCount: 0,
            confidenceBps: 9400
        });
        bytes memory aiSig = _signAIAttestation(aiSignerPk, att);

        registry.submitAttempt(
            fileKey,
            sampleDocHashes,
            declarationHash,
            att,
            plantSig,
            aiSig
        );

        // Verifier signs with 0 redResolved
        DamgaRegistry.Verification memory vrf = DamgaRegistry.Verification({
            fileKey: fileKey,
            attemptIndex: 0,
            docsRoot: docsRoot,
            resultHash: resultHash,
            resolutionsHash: bytes32(0),
            redResolved: 0,
            yellowChecked: 0,
            emissionsCommitment: 100,
            scrapCommitment: 200,
            emissionsLimit: 150,
            minScrapShare: 900,
            vcHash: keccak256(bytes("vc_01"))
        });
        bytes memory verifierSig = _signVerification(verifierPk, vrf);

        vm.expectRevert(DamgaRegistry.OpenRedFlags.selector);
        registry.issuePassport(
            fileKey,
            0,
            sampleDocHashes,
            vrf,
            verifierSig,
            dummyProof,
            dummyProof
        );
    }

    function test_PassWhen_RedAttemptWithResolutions() public {
        bytes32 docsRoot = registry.computeDocsRoot(sampleDocHashes);
        bytes32 inputHash = keccak256(abi.encode(docsRoot, declarationHash));
        bytes32 resultHash = keccak256(bytes("ai_result_red_resolved"));

        bytes memory plantSig = _signPlantDeclaration(
            plantSignerPk,
            fileKey,
            docsRoot,
            declarationHash,
            0
        );

        DamgaRegistry.AIAttestation memory att = DamgaRegistry.AIAttestation({
            fileKey: fileKey,
            inputHash: inputHash,
            modelHash: modelHash,
            rulesetHash: rulesetHash,
            resultHash: resultHash,
            status: 2, // RED
            redCount: 2,
            yellowCount: 0,
            missingCount: 0,
            confidenceBps: 9400
        });
        bytes memory aiSig = _signAIAttestation(aiSignerPk, att);

        registry.submitAttempt(
            fileKey,
            sampleDocHashes,
            declarationHash,
            att,
            plantSig,
            aiSig
        );

        // Verifier signs with redResolved == 2 and resolutionsHash
        DamgaRegistry.Verification memory vrf = DamgaRegistry.Verification({
            fileKey: fileKey,
            attemptIndex: 0,
            docsRoot: docsRoot,
            resultHash: resultHash,
            resolutionsHash: keccak256(bytes("resolved_both_pig_iron_invoices")),
            redResolved: 2,
            yellowChecked: 0,
            emissionsCommitment: 100,
            scrapCommitment: 200,
            emissionsLimit: 150,
            minScrapShare: 900,
            vcHash: keccak256(bytes("vc_01"))
        });
        bytes memory verifierSig = _signVerification(verifierPk, vrf);

        uint256 pId = registry.issuePassport(
            fileKey,
            0,
            sampleDocHashes,
            vrf,
            verifierSig,
            dummyProof,
            dummyProof
        );
        assertEq(pId, 1);
    }

    function test_RevertWhen_MissingEvidence() public {
        bytes32 docsRoot = registry.computeDocsRoot(sampleDocHashes);
        bytes32 inputHash = keccak256(abi.encode(docsRoot, declarationHash));
        bytes32 resultHash = keccak256(bytes("ai_result_missing"));

        bytes memory plantSig = _signPlantDeclaration(
            plantSignerPk,
            fileKey,
            docsRoot,
            declarationHash,
            0
        );

        DamgaRegistry.AIAttestation memory att = DamgaRegistry.AIAttestation({
            fileKey: fileKey,
            inputHash: inputHash,
            modelHash: modelHash,
            rulesetHash: rulesetHash,
            resultHash: resultHash,
            status: 3, // MISSING
            redCount: 0,
            yellowCount: 0,
            missingCount: 1,
            confidenceBps: 9000
        });
        bytes memory aiSig = _signAIAttestation(aiSignerPk, att);

        registry.submitAttempt(
            fileKey,
            sampleDocHashes,
            declarationHash,
            att,
            plantSig,
            aiSig
        );

        DamgaRegistry.Verification memory vrf = DamgaRegistry.Verification({
            fileKey: fileKey,
            attemptIndex: 0,
            docsRoot: docsRoot,
            resultHash: resultHash,
            resolutionsHash: bytes32(0),
            redResolved: 0,
            yellowChecked: 0,
            emissionsCommitment: 100,
            scrapCommitment: 200,
            emissionsLimit: 150,
            minScrapShare: 900,
            vcHash: keccak256(bytes("vc_01"))
        });
        bytes memory verifierSig = _signVerification(verifierPk, vrf);

        vm.expectRevert(DamgaRegistry.MissingEvidence.selector);
        registry.issuePassport(
            fileKey,
            0,
            sampleDocHashes,
            vrf,
            verifierSig,
            dummyProof,
            dummyProof
        );
    }

    function test_RevertWhen_YellowUnchecked() public {
        bytes32 docsRoot = registry.computeDocsRoot(sampleDocHashes);
        bytes32 inputHash = keccak256(abi.encode(docsRoot, declarationHash));
        bytes32 resultHash = keccak256(bytes("ai_result_yellow"));

        bytes memory plantSig = _signPlantDeclaration(
            plantSignerPk,
            fileKey,
            docsRoot,
            declarationHash,
            0
        );

        DamgaRegistry.AIAttestation memory att = DamgaRegistry.AIAttestation({
            fileKey: fileKey,
            inputHash: inputHash,
            modelHash: modelHash,
            rulesetHash: rulesetHash,
            resultHash: resultHash,
            status: 1, // YELLOW
            redCount: 0,
            yellowCount: 2,
            missingCount: 0,
            confidenceBps: 9600
        });
        bytes memory aiSig = _signAIAttestation(aiSignerPk, att);

        registry.submitAttempt(
            fileKey,
            sampleDocHashes,
            declarationHash,
            att,
            plantSig,
            aiSig
        );

        // Verifier only checked 1 out of 2
        DamgaRegistry.Verification memory vrf = DamgaRegistry.Verification({
            fileKey: fileKey,
            attemptIndex: 0,
            docsRoot: docsRoot,
            resultHash: resultHash,
            resolutionsHash: bytes32(0),
            redResolved: 0,
            yellowChecked: 1,
            emissionsCommitment: 100,
            scrapCommitment: 200,
            emissionsLimit: 150,
            minScrapShare: 900,
            vcHash: keccak256(bytes("vc_01"))
        });
        bytes memory verifierSig = _signVerification(verifierPk, vrf);

        vm.expectRevert(DamgaRegistry.UncheckedYellowFlags.selector);
        registry.issuePassport(
            fileKey,
            0,
            sampleDocHashes,
            vrf,
            verifierSig,
            dummyProof,
            dummyProof
        );
    }

    function test_RevertWhen_DocsChanged() public {
        bytes32 docsRoot = registry.computeDocsRoot(sampleDocHashes);
        bytes32 inputHash = keccak256(abi.encode(docsRoot, declarationHash));
        bytes32 resultHash = keccak256(bytes("ai_result_clean"));

        bytes memory plantSig = _signPlantDeclaration(
            plantSignerPk,
            fileKey,
            docsRoot,
            declarationHash,
            0
        );

        DamgaRegistry.AIAttestation memory att = DamgaRegistry.AIAttestation({
            fileKey: fileKey,
            inputHash: inputHash,
            modelHash: modelHash,
            rulesetHash: rulesetHash,
            resultHash: resultHash,
            status: 0,
            redCount: 0,
            yellowCount: 0,
            missingCount: 0,
            confidenceBps: 9800
        });
        bytes memory aiSig = _signAIAttestation(aiSignerPk, att);

        registry.submitAttempt(
            fileKey,
            sampleDocHashes,
            declarationHash,
            att,
            plantSig,
            aiSig
        );

        DamgaRegistry.Verification memory vrf = DamgaRegistry.Verification({
            fileKey: fileKey,
            attemptIndex: 0,
            docsRoot: docsRoot,
            resultHash: resultHash,
            resolutionsHash: bytes32(0),
            redResolved: 0,
            yellowChecked: 0,
            emissionsCommitment: 100,
            scrapCommitment: 200,
            emissionsLimit: 150,
            minScrapShare: 900,
            vcHash: keccak256(bytes("vc_01"))
        });
        bytes memory verifierSig = _signVerification(verifierPk, vrf);

        // Mutate one doc hash
        bytes32[] memory alteredDocs = new bytes32[](3);
        alteredDocs[0] = sampleDocHashes[0];
        alteredDocs[1] = sampleDocHashes[1];
        alteredDocs[2] = keccak256(bytes("tampered_weighbridge"));

        vm.expectRevert(DamgaRegistry.DocsChanged.selector);
        registry.issuePassport(
            fileKey,
            0,
            alteredDocs,
            vrf,
            verifierSig,
            dummyProof,
            dummyProof
        );
    }

    function test_RevertWhen_DocReusedAcrossFiles() public {
        bytes32 docsRoot1 = registry.computeDocsRoot(sampleDocHashes);
        bytes32 inputHash1 = keccak256(abi.encode(docsRoot1, declarationHash));
        bytes32 resultHash1 = keccak256(bytes("ai_result_1"));

        bytes memory plantSig1 = _signPlantDeclaration(
            plantSignerPk,
            fileKey,
            docsRoot1,
            declarationHash,
            0
        );
        DamgaRegistry.AIAttestation memory att1 = DamgaRegistry.AIAttestation({
            fileKey: fileKey,
            inputHash: inputHash1,
            modelHash: modelHash,
            rulesetHash: rulesetHash,
            resultHash: resultHash1,
            status: 0,
            redCount: 0,
            yellowCount: 0,
            missingCount: 0,
            confidenceBps: 9800
        });
        bytes memory aiSig1 = _signAIAttestation(aiSignerPk, att1);

        registry.submitAttempt(
            fileKey,
            sampleDocHashes,
            declarationHash,
            att1,
            plantSig1,
            aiSig1
        );

        // Check isDocUsed view
        assertTrue(registry.docToFileKey(sampleDocHashes[0]) != bytes32(0));

        // Second file for a different year
        bytes32 fileKey2 = registry.registerFile(plantId, 2027, cnCode);
        bytes32[] memory overlappingDocs = new bytes32[](2);
        overlappingDocs[0] = sampleDocHashes[0]; // reused!
        overlappingDocs[1] = keccak256(bytes("new_doc_2027"));

        bytes32 docsRoot2 = registry.computeDocsRoot(overlappingDocs);
        bytes32 inputHash2 = keccak256(abi.encode(docsRoot2, declarationHash));

        bytes memory plantSig2 = _signPlantDeclaration(
            plantSignerPk,
            fileKey2,
            docsRoot2,
            declarationHash,
            0
        );
        DamgaRegistry.AIAttestation memory att2 = DamgaRegistry.AIAttestation({
            fileKey: fileKey2,
            inputHash: inputHash2,
            modelHash: modelHash,
            rulesetHash: rulesetHash,
            resultHash: keccak256(bytes("ai_result_2")),
            status: 0,
            redCount: 0,
            yellowCount: 0,
            missingCount: 0,
            confidenceBps: 9800
        });
        bytes memory aiSig2 = _signAIAttestation(aiSignerPk, att2);

        vm.expectRevert(DamgaRegistry.DocReused.selector);
        registry.submitAttempt(
            fileKey2,
            overlappingDocs,
            declarationHash,
            att2,
            plantSig2,
            aiSig2
        );
    }

    function test_RevertWhen_PassportExists() public {
        // Issue passport 1
        test_HappyPath();

        // Attempting to issue again on same active passport reverts
        bytes32 docsRoot = registry.computeDocsRoot(sampleDocHashes);
        bytes32 resultHash = keccak256(bytes("ai_result_clean_v1"));

        DamgaRegistry.Verification memory vrf = DamgaRegistry.Verification({
            fileKey: fileKey,
            attemptIndex: 0,
            docsRoot: docsRoot,
            resultHash: resultHash,
            resolutionsHash: bytes32(0),
            redResolved: 0,
            yellowChecked: 0,
            emissionsCommitment: 123456789,
            scrapCommitment: 987654321,
            emissionsLimit: 150,
            minScrapShare: 900,
            vcHash: keccak256(bytes("vc_hash_01"))
        });
        bytes memory verifierSig = _signVerification(verifierPk, vrf);

        vm.expectRevert(DamgaRegistry.PassportExists.selector);
        registry.issuePassport(
            fileKey,
            0,
            sampleDocHashes,
            vrf,
            verifierSig,
            dummyProof,
            dummyProof
        );
    }

    function test_RevertWhen_NotLatestAttempt() public {
        // Submit attempt 0
        bytes32 docsRoot = registry.computeDocsRoot(sampleDocHashes);
        bytes32 inputHash = keccak256(abi.encode(docsRoot, declarationHash));
        bytes32 resultHash0 = keccak256(bytes("ai_result_0"));

        bytes memory plantSig0 = _signPlantDeclaration(
            plantSignerPk,
            fileKey,
            docsRoot,
            declarationHash,
            0
        );
        DamgaRegistry.AIAttestation memory att0 = DamgaRegistry.AIAttestation({
            fileKey: fileKey,
            inputHash: inputHash,
            modelHash: modelHash,
            rulesetHash: rulesetHash,
            resultHash: resultHash0,
            status: 0,
            redCount: 0,
            yellowCount: 0,
            missingCount: 0,
            confidenceBps: 9500
        });
        bytes memory aiSig0 = _signAIAttestation(aiSignerPk, att0);
        registry.submitAttempt(fileKey, sampleDocHashes, declarationHash, att0, plantSig0, aiSig0);

        // Submit attempt 1
        bytes32 resultHash1 = keccak256(bytes("ai_result_1"));
        bytes memory plantSig1 = _signPlantDeclaration(
            plantSignerPk,
            fileKey,
            docsRoot,
            declarationHash,
            1
        );
        DamgaRegistry.AIAttestation memory att1 = DamgaRegistry.AIAttestation({
            fileKey: fileKey,
            inputHash: inputHash,
            modelHash: modelHash,
            rulesetHash: rulesetHash,
            resultHash: resultHash1,
            status: 0,
            redCount: 0,
            yellowCount: 0,
            missingCount: 0,
            confidenceBps: 9900
        });
        bytes memory aiSig1 = _signAIAttestation(aiSignerPk, att1);
        registry.submitAttempt(fileKey, sampleDocHashes, declarationHash, att1, plantSig1, aiSig1);

        // Try issuing passport for attempt 0
        DamgaRegistry.Verification memory vrf0 = DamgaRegistry.Verification({
            fileKey: fileKey,
            attemptIndex: 0,
            docsRoot: docsRoot,
            resultHash: resultHash0,
            resolutionsHash: bytes32(0),
            redResolved: 0,
            yellowChecked: 0,
            emissionsCommitment: 100,
            scrapCommitment: 200,
            emissionsLimit: 150,
            minScrapShare: 900,
            vcHash: keccak256(bytes("vc_0"))
        });
        bytes memory verifierSig = _signVerification(verifierPk, vrf0);

        vm.expectRevert(DamgaRegistry.NotLatestAttempt.selector);
        registry.issuePassport(
            fileKey,
            0,
            sampleDocHashes,
            vrf0,
            verifierSig,
            dummyProof,
            dummyProof
        );
    }

    function test_RevertWhen_BadSignatures() public {
        bytes32 docsRoot = registry.computeDocsRoot(sampleDocHashes);
        bytes32 inputHash = keccak256(abi.encode(docsRoot, declarationHash));
        bytes32 resultHash = keccak256(bytes("ai_result"));

        // 1. Bad plant signature
        bytes memory badPlantSig = _signPlantDeclaration(
            unauthorizedPk,
            fileKey,
            docsRoot,
            declarationHash,
            0
        );
        DamgaRegistry.AIAttestation memory att = DamgaRegistry.AIAttestation({
            fileKey: fileKey,
            inputHash: inputHash,
            modelHash: modelHash,
            rulesetHash: rulesetHash,
            resultHash: resultHash,
            status: 0,
            redCount: 0,
            yellowCount: 0,
            missingCount: 0,
            confidenceBps: 9800
        });
        bytes memory goodAiSig = _signAIAttestation(aiSignerPk, att);

        vm.expectRevert(DamgaRegistry.BadSignature.selector);
        registry.submitAttempt(
            fileKey,
            sampleDocHashes,
            declarationHash,
            att,
            badPlantSig,
            goodAiSig
        );

        // 2. Bad AI signature
        bytes memory goodPlantSig = _signPlantDeclaration(
            plantSignerPk,
            fileKey,
            docsRoot,
            declarationHash,
            0
        );
        bytes memory badAiSig = _signAIAttestation(unauthorizedPk, att);

        vm.expectRevert(DamgaRegistry.BadSignature.selector);
        registry.submitAttempt(
            fileKey,
            sampleDocHashes,
            declarationHash,
            att,
            goodPlantSig,
            badAiSig
        );

        // Now submit with valid signatures to test bad verifier signature
        registry.submitAttempt(
            fileKey,
            sampleDocHashes,
            declarationHash,
            att,
            goodPlantSig,
            goodAiSig
        );

        // 3. Bad verifier signature
        DamgaRegistry.Verification memory vrf = DamgaRegistry.Verification({
            fileKey: fileKey,
            attemptIndex: 0,
            docsRoot: docsRoot,
            resultHash: resultHash,
            resolutionsHash: bytes32(0),
            redResolved: 0,
            yellowChecked: 0,
            emissionsCommitment: 100,
            scrapCommitment: 200,
            emissionsLimit: 150,
            minScrapShare: 900,
            vcHash: keccak256(bytes("vc_01"))
        });
        bytes memory badVerifierSig = _signVerification(unauthorizedPk, vrf);

        vm.expectRevert(DamgaRegistry.BadSignature.selector);
        registry.issuePassport(
            fileKey,
            0,
            sampleDocHashes,
            vrf,
            badVerifierSig,
            dummyProof,
            dummyProof
        );
    }

    function test_RevertWhen_UnapprovedModel() public {
        bytes32 docsRoot = registry.computeDocsRoot(sampleDocHashes);
        bytes32 inputHash = keccak256(abi.encode(docsRoot, declarationHash));
        bytes32 unapprovedModelHash = keccak256(bytes("unapproved_ai_model"));

        bytes memory plantSig = _signPlantDeclaration(
            plantSignerPk,
            fileKey,
            docsRoot,
            declarationHash,
            0
        );

        DamgaRegistry.AIAttestation memory att = DamgaRegistry.AIAttestation({
            fileKey: fileKey,
            inputHash: inputHash,
            modelHash: unapprovedModelHash,
            rulesetHash: rulesetHash,
            resultHash: keccak256(bytes("res")),
            status: 0,
            redCount: 0,
            yellowCount: 0,
            missingCount: 0,
            confidenceBps: 9800
        });
        bytes memory aiSig = _signAIAttestation(aiSignerPk, att);

        vm.expectRevert(DamgaRegistry.UnapprovedModel.selector);
        registry.submitAttempt(
            fileKey,
            sampleDocHashes,
            declarationHash,
            att,
            plantSig,
            aiSig
        );
    }

    function test_RevertWhen_UnapprovedRuleset() public {
        bytes32 docsRoot = registry.computeDocsRoot(sampleDocHashes);
        bytes32 inputHash = keccak256(abi.encode(docsRoot, declarationHash));
        bytes32 unapprovedRuleset = keccak256(bytes("unapproved_ruleset"));

        bytes memory plantSig = _signPlantDeclaration(
            plantSignerPk,
            fileKey,
            docsRoot,
            declarationHash,
            0
        );

        DamgaRegistry.AIAttestation memory att = DamgaRegistry.AIAttestation({
            fileKey: fileKey,
            inputHash: inputHash,
            modelHash: modelHash,
            rulesetHash: unapprovedRuleset,
            resultHash: keccak256(bytes("res")),
            status: 0,
            redCount: 0,
            yellowCount: 0,
            missingCount: 0,
            confidenceBps: 9800
        });
        bytes memory aiSig = _signAIAttestation(aiSignerPk, att);

        vm.expectRevert(DamgaRegistry.UnapprovedRuleset.selector);
        registry.submitAttempt(
            fileKey,
            sampleDocHashes,
            declarationHash,
            att,
            plantSig,
            aiSig
        );
    }

    function test_RevertWhen_InvalidProof() public {
        bytes32 docsRoot = registry.computeDocsRoot(sampleDocHashes);
        bytes32 inputHash = keccak256(abi.encode(docsRoot, declarationHash));
        bytes32 resultHash = keccak256(bytes("ai_result_clean_v1"));

        bytes memory plantSig = _signPlantDeclaration(
            plantSignerPk,
            fileKey,
            docsRoot,
            declarationHash,
            0
        );
        DamgaRegistry.AIAttestation memory att = DamgaRegistry.AIAttestation({
            fileKey: fileKey,
            inputHash: inputHash,
            modelHash: modelHash,
            rulesetHash: rulesetHash,
            resultHash: resultHash,
            status: 0,
            redCount: 0,
            yellowCount: 0,
            missingCount: 0,
            confidenceBps: 9800
        });
        bytes memory aiSig = _signAIAttestation(aiSignerPk, att);

        registry.submitAttempt(
            fileKey,
            sampleDocHashes,
            declarationHash,
            att,
            plantSig,
            aiSig
        );

        DamgaRegistry.Verification memory vrf = DamgaRegistry.Verification({
            fileKey: fileKey,
            attemptIndex: 0,
            docsRoot: docsRoot,
            resultHash: resultHash,
            resolutionsHash: bytes32(0),
            redResolved: 0,
            yellowChecked: 0,
            emissionsCommitment: 123456789,
            scrapCommitment: 987654321,
            emissionsLimit: 150,
            minScrapShare: 900,
            vcHash: keccak256(bytes("vc_hash_01"))
        });
        bytes memory verifierSig = _signVerification(verifierPk, vrf);

        // Make mock verifier fail
        mockEmissionsVerifier.setShouldPass(false);

        vm.expectRevert(DamgaRegistry.InvalidProof.selector);
        registry.issuePassport(
            fileKey,
            0,
            sampleDocHashes,
            vrf,
            verifierSig,
            dummyProof,
            dummyProof
        );
    }

    function test_RevokeWithSupersede_And_Version2LinksPrevPassportId() public {
        // Issue version 1
        test_HappyPath();
        assertEq(registry.passportOfFile(fileKey), 1);

        // Verifier revokes with supersede = true
        bytes32 reasonHash = keccak256(bytes("annual_calibration_update"));
        vm.prank(verifierSigner);
        registry.revokePassport(1, reasonHash, true);

        DamgaRegistry.Passport memory p1 = registry.getPassport(1);
        assertEq(uint8(p1.status), uint8(DamgaRegistry.PassportStatus.SUPERSEDED));

        // Submit new attempt 1
        bytes32 docsRoot = registry.computeDocsRoot(sampleDocHashes);
        bytes32 inputHash = keccak256(abi.encode(docsRoot, declarationHash));
        bytes32 resultHashV2 = keccak256(bytes("ai_result_v2"));

        bytes memory plantSig = _signPlantDeclaration(
            plantSignerPk,
            fileKey,
            docsRoot,
            declarationHash,
            1 // nonce is 1 now
        );
        DamgaRegistry.AIAttestation memory att = DamgaRegistry.AIAttestation({
            fileKey: fileKey,
            inputHash: inputHash,
            modelHash: modelHash,
            rulesetHash: rulesetHash,
            resultHash: resultHashV2,
            status: 0,
            redCount: 0,
            yellowCount: 0,
            missingCount: 0,
            confidenceBps: 9900
        });
        bytes memory aiSig = _signAIAttestation(aiSignerPk, att);
        registry.submitAttempt(
            fileKey,
            sampleDocHashes,
            declarationHash,
            att,
            plantSig,
            aiSig
        );

        // Issue passport version 2
        DamgaRegistry.Verification memory vrf2 = DamgaRegistry.Verification({
            fileKey: fileKey,
            attemptIndex: 1,
            docsRoot: docsRoot,
            resultHash: resultHashV2,
            resolutionsHash: bytes32(0),
            redResolved: 0,
            yellowChecked: 0,
            emissionsCommitment: 111111,
            scrapCommitment: 222222,
            emissionsLimit: 140,
            minScrapShare: 920,
            vcHash: keccak256(bytes("vc_hash_02"))
        });
        bytes memory verifierSig2 = _signVerification(verifierPk, vrf2);

        uint256 passportId2 = registry.issuePassport(
            fileKey,
            1,
            sampleDocHashes,
            vrf2,
            verifierSig2,
            dummyProof,
            dummyProof
        );

        assertEq(passportId2, 2);
        assertEq(registry.passportOfFile(fileKey), 2);

        DamgaRegistry.Passport memory p2 = registry.getPassport(2);
        assertEq(p2.version, 2);
        assertEq(p2.prevPassportId, 1);
        assertEq(uint8(p2.status), uint8(DamgaRegistry.PassportStatus.ACTIVE));
    }

    function test_RevokeWithoutSupersede() public {
        test_HappyPath();

        bytes32 reasonHash = keccak256(bytes("fraudulent_report"));
        vm.prank(verifierSigner);
        registry.revokePassport(1, reasonHash, false);

        DamgaRegistry.Passport memory p = registry.getPassport(1);
        assertEq(uint8(p.status), uint8(DamgaRegistry.PassportStatus.REVOKED));

        // Submit new attempt 1
        bytes32 docsRoot = registry.computeDocsRoot(sampleDocHashes);
        bytes32 inputHash = keccak256(abi.encode(docsRoot, declarationHash));
        bytes32 resultHashV2 = keccak256(bytes("ai_result_v2"));

        bytes memory plantSig = _signPlantDeclaration(
            plantSignerPk,
            fileKey,
            docsRoot,
            declarationHash,
            1
        );
        DamgaRegistry.AIAttestation memory att = DamgaRegistry.AIAttestation({
            fileKey: fileKey,
            inputHash: inputHash,
            modelHash: modelHash,
            rulesetHash: rulesetHash,
            resultHash: resultHashV2,
            status: 0,
            redCount: 0,
            yellowCount: 0,
            missingCount: 0,
            confidenceBps: 9900
        });
        bytes memory aiSig = _signAIAttestation(aiSignerPk, att);
        registry.submitAttempt(
            fileKey,
            sampleDocHashes,
            declarationHash,
            att,
            plantSig,
            aiSig
        );

        DamgaRegistry.Verification memory vrf2 = DamgaRegistry.Verification({
            fileKey: fileKey,
            attemptIndex: 1,
            docsRoot: docsRoot,
            resultHash: resultHashV2,
            resolutionsHash: bytes32(0),
            redResolved: 0,
            yellowChecked: 0,
            emissionsCommitment: 111111,
            scrapCommitment: 222222,
            emissionsLimit: 140,
            minScrapShare: 920,
            vcHash: keccak256(bytes("vc_hash_02"))
        });
        bytes memory verifierSig2 = _signVerification(verifierPk, vrf2);

        // Cannot issue new version without supersede
        vm.expectRevert(DamgaRegistry.PassportExists.selector);
        registry.issuePassport(
            fileKey,
            1,
            sampleDocHashes,
            vrf2,
            verifierSig2,
            dummyProof,
            dummyProof
        );
    }

    function test_DisputePassport() public {
        test_HappyPath();

        bytes32 disputeReason = keccak256(bytes("customs_sample_divergence"));

        // Non-owner cannot dispute
        vm.prank(unauthorizedSigner);
        vm.expectRevert();
        registry.disputePassport(1, disputeReason);

        // Owner disputes
        registry.disputePassport(1, disputeReason);

        DamgaRegistry.Passport memory p = registry.getPassport(1);
        assertEq(uint8(p.status), uint8(DamgaRegistry.PassportStatus.DISPUTED));
    }

    function test_AttemptsHistoryKeepsAllAttempts() public {
        bytes32 docsRoot = registry.computeDocsRoot(sampleDocHashes);
        bytes32 inputHash = keccak256(abi.encode(docsRoot, declarationHash));

        // Attempt 0: RED
        bytes memory pSig0 = _signPlantDeclaration(plantSignerPk, fileKey, docsRoot, declarationHash, 0);
        DamgaRegistry.AIAttestation memory att0 = DamgaRegistry.AIAttestation({
            fileKey: fileKey,
            inputHash: inputHash,
            modelHash: modelHash,
            rulesetHash: rulesetHash,
            resultHash: keccak256(bytes("res_0")),
            status: 2, // RED
            redCount: 2,
            yellowCount: 0,
            missingCount: 0,
            confidenceBps: 9200
        });
        bytes memory aiSig0 = _signAIAttestation(aiSignerPk, att0);
        registry.submitAttempt(fileKey, sampleDocHashes, declarationHash, att0, pSig0, aiSig0);

        // Attempt 1: RED
        bytes memory pSig1 = _signPlantDeclaration(plantSignerPk, fileKey, docsRoot, declarationHash, 1);
        DamgaRegistry.AIAttestation memory att1 = DamgaRegistry.AIAttestation({
            fileKey: fileKey,
            inputHash: inputHash,
            modelHash: modelHash,
            rulesetHash: rulesetHash,
            resultHash: keccak256(bytes("res_1")),
            status: 2, // RED
            redCount: 1,
            yellowCount: 0,
            missingCount: 0,
            confidenceBps: 9400
        });
        bytes memory aiSig1 = _signAIAttestation(aiSignerPk, att1);
        registry.submitAttempt(fileKey, sampleDocHashes, declarationHash, att1, pSig1, aiSig1);

        // Attempt 2: GREEN
        bytes memory pSig2 = _signPlantDeclaration(plantSignerPk, fileKey, docsRoot, declarationHash, 2);
        DamgaRegistry.AIAttestation memory att2 = DamgaRegistry.AIAttestation({
            fileKey: fileKey,
            inputHash: inputHash,
            modelHash: modelHash,
            rulesetHash: rulesetHash,
            resultHash: keccak256(bytes("res_2")),
            status: 0, // GREEN
            redCount: 0,
            yellowCount: 0,
            missingCount: 0,
            confidenceBps: 9800
        });
        bytes memory aiSig2 = _signAIAttestation(aiSignerPk, att2);
        registry.submitAttempt(fileKey, sampleDocHashes, declarationHash, att2, pSig2, aiSig2);

        DamgaRegistry.Attempt[] memory history = registry.getAttempts(fileKey);
        assertEq(history.length, 3);
        assertEq(history[0].status, 2);
        assertEq(history[0].redCount, 2);
        assertEq(history[1].status, 2);
        assertEq(history[1].redCount, 1);
        assertEq(history[2].status, 0);
        assertEq(history[2].redCount, 0);
    }

    function test_RealVerifiersDeployment() public {
        EmissionsLeLimitVerifier realEmissions = new EmissionsLeLimitVerifier();
        ScrapShareGeVerifier realScrap = new ScrapShareGeVerifier();

        DamgaRegistry realRegistry = new DamgaRegistry(
            address(realEmissions),
            address(realScrap)
        );

        assertEq(address(realRegistry.emissionsVerifier()), address(realEmissions));
        assertEq(address(realRegistry.scrapVerifier()), address(realScrap));
    }
}
