import { ethers } from "ethers";

/**
 * Hashes a File object's raw bytes with keccak256, producing a
 * 0x-prefixed bytes32 hex string that matches the contract's expected
 * input type exactly.
 */
export async function hashFile(file) {
  const buffer = await file.arrayBuffer();
  const bytes = new Uint8Array(buffer);
  return ethers.utils.keccak256(bytes);
}
