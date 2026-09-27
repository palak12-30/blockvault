// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

contract DocumentVerification {

    struct Document {
        address owner;
        uint256 timestamp;
    }

    mapping(bytes32 => Document) public documents;

    event DocumentUploaded(bytes32 indexed hash, address indexed owner, uint256 timestamp);

    function uploadDocument(bytes32 hash) public {
        require(documents[hash].timestamp == 0, "Document already exists");

        documents[hash] = Document(msg.sender, block.timestamp);

        emit DocumentUploaded(hash, msg.sender, block.timestamp);
    }

    function verifyDocument(bytes32 hash) public view returns (bool, address, uint256) {
        Document memory doc = documents[hash];

        if (doc.timestamp == 0) {
            return (false, address(0), 0);
        }

        return (true, doc.owner, doc.timestamp);
    }
}