

import { expect } from "chai";
import { ethers } from "hardhat";
import { Contract, Signer } from "ethers";
 
describe("DocumentVerification", function () {
  let contract: Contract;
  let owner: Signer;
  let other: Signer;
 
  // Example hash - in real use this comes from hashing a document (e.g. keccak256 of its bytes)
  const sampleHash = ethers.utils.keccak256(ethers.utils.toUtf8Bytes("sample-document-content"));
  const otherHash = ethers.utils.keccak256(ethers.utils.toUtf8Bytes("a-different-document"));
 
  beforeEach(async function () {
    [owner, other] = await ethers.getSigners();
 
    const Factory = await ethers.getContractFactory("DocumentVerification");
    contract = await Factory.deploy();
    await contract.deployed();
  });
 
  it("should register a new document and emit an event", async function () {
    const ownerAddress = await owner.getAddress();
 
    const tx = await contract.uploadDocument(sampleHash);
    const receipt = await tx.wait();
 
    const event = receipt.events?.find((e: any) => e.event === "DocumentUploaded");
 
    expect(event).to.not.be.undefined;
    expect(event.args.hash).to.equal(sampleHash);
    expect(event.args.owner).to.equal(ownerAddress);
    expect(event.args.timestamp.gt(0)).to.equal(true);
  });
 
  it("should verify an uploaded document correctly", async function () {
    const ownerAddress = await owner.getAddress();
 
    await contract.uploadDocument(sampleHash);
 
    const [exists, docOwner, timestamp] = await contract.verifyDocument(sampleHash);
 
    expect(exists).to.equal(true);
    expect(docOwner).to.equal(ownerAddress);
    expect(timestamp.gt(0)).to.equal(true);
  });
 
  it("should return false for a document that was never uploaded", async function () {
    const [exists, docOwner, timestamp] = await contract.verifyDocument(otherHash);
 
    expect(exists).to.equal(false);
    expect(docOwner).to.equal(ethers.constants.AddressZero);
    expect(timestamp.eq(0)).to.equal(true);
  });
 
  it("should reject uploading the same document hash twice", async function () {
    await contract.uploadDocument(sampleHash);
 
    let errorMessage = "";
    try {
      await contract.uploadDocument(sampleHash);
    } catch (err: any) {
      errorMessage = err.message;
    }
 
    expect(errorMessage).to.include("Document already exists");
  });
 
  it("should allow different accounts to upload different documents", async function () {
    const otherAddress = await other.getAddress();
 
    await contract.connect(other).uploadDocument(otherHash);
 
    const [exists, docOwner] = await contract.verifyDocument(otherHash);
 
    expect(exists).to.equal(true);
    expect(docOwner).to.equal(otherAddress);
  });
 
  // Helper: approximates the timestamp of the next mined block.
  // Only reliable right before a transaction is sent in the same test.
  async function getBlockTimestamp(): Promise<number> {
    const block = await ethers.provider.getBlock("latest");
    return block.timestamp + 1;
  }
});
 
