// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import {Script, console} from "forge-std/Script.sol";
import {DamgaRegistry} from "../src/DamgaRegistry.sol";
import {EmissionsLeLimitVerifier} from "../src/verifiers/EmissionsLeLimitVerifier.sol";
import {ScrapShareGeVerifier} from "../src/verifiers/ScrapShareGeVerifier.sol";

contract DeployScript is Script {
    function run() external returns (address registryAddr, address emissionsVerifierAddr, address scrapVerifierAddr) {
        uint256 deployerPk = vm.envOr("RELAYER_PRIVATE_KEY", uint256(0));

        if (deployerPk != 0) {
            vm.startBroadcast(deployerPk);
        } else {
            vm.startBroadcast();
        }

        console.log("Deploying Groth16 Verifiers...");
        EmissionsLeLimitVerifier emissionsVerifier = new EmissionsLeLimitVerifier();
        ScrapShareGeVerifier scrapVerifier = new ScrapShareGeVerifier();

        emissionsVerifierAddr = address(emissionsVerifier);
        scrapVerifierAddr = address(scrapVerifier);

        console.log("EmissionsLeLimitVerifier deployed at:", emissionsVerifierAddr);
        console.log("ScrapShareGeVerifier deployed at:", scrapVerifierAddr);

        console.log("Deploying DamgaRegistry...");
        DamgaRegistry registry = new DamgaRegistry(emissionsVerifierAddr, scrapVerifierAddr);
        registryAddr = address(registry);
        console.log("DamgaRegistry deployed at:", registryAddr);

        // --- Role Configuration ---

        // 1. Plant Signer for Aliağa Demo Steel Works (fictional)
        bytes32 plantId = keccak256(bytes("TR-ALIAGA-DEMO-001"));
        uint256 plantPk = vm.envOr("PLANT_SIGNER_PRIVATE_KEY", uint256(0));
        address plantSigner = plantPk != 0 ? vm.addr(plantPk) : vm.envOr("PLANT_SIGNER_ADDRESS", address(0));

        if (plantSigner != address(0)) {
            registry.setPlantSigner(plantId, plantSigner);
            console.log("Configured plant signer for TR-ALIAGA-DEMO-001:", plantSigner);
        } else {
            console.log("Notice: Neither PLANT_SIGNER_PRIVATE_KEY nor PLANT_SIGNER_ADDRESS provided. Skipping plant signer setup.");
        }

        // 2. AI Signer
        uint256 aiPk = vm.envOr("AI_SIGNER_PRIVATE_KEY", uint256(0));
        address aiSigner = aiPk != 0 ? vm.addr(aiPk) : vm.envOr("AI_SIGNER_ADDRESS", address(0));

        if (aiSigner != address(0)) {
            registry.setAISigner(aiSigner, true);
            console.log("Configured AI signer:", aiSigner);
        } else {
            console.log("Notice: Neither AI_SIGNER_PRIVATE_KEY nor AI_SIGNER_ADDRESS provided. Skipping AI signer setup.");
        }

        // 3. Demo Verifier ("Demo Verification GmbH (fictional)")
        uint256 verifierPk = vm.envOr("DEMO_VERIFIER_PRIVATE_KEY", uint256(0));
        address verifierSigner = verifierPk != 0 ? vm.addr(verifierPk) : vm.envOr("DEMO_VERIFIER_ADDRESS", address(0));

        if (verifierSigner != address(0)) {
            registry.setVerifier(verifierSigner, true, "Demo Verification GmbH (fictional)");
            console.log("Configured verifier Demo Verification GmbH (fictional):", verifierSigner);
        } else {
            console.log("Notice: Neither DEMO_VERIFIER_PRIVATE_KEY nor DEMO_VERIFIER_ADDRESS provided. Skipping verifier setup.");
        }

        // 4-5. Model and ruleset are approved only when given, so no placeholder hash goes on-chain.
        // The owner can approve them later with setApprovedModel / setApprovedRuleset.
        bytes32 modelHash = vm.envOr("MODEL_HASH", bytes32(0));
        if (modelHash != bytes32(0)) {
            registry.setApprovedModel(modelHash, true);
            console.log("Approved modelHash:");
            console.logBytes32(modelHash);
        }
        bytes32 rulesetHash = vm.envOr("RULESET_HASH", bytes32(0));
        if (rulesetHash != bytes32(0)) {
            registry.setApprovedRuleset(rulesetHash, true);
            console.log("Approved rulesetHash:");
            console.logBytes32(rulesetHash);
        }

        vm.stopBroadcast();

        console.log("Deployment and role initialization completed successfully.");
    }
}
