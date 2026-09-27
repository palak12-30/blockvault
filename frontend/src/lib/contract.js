// Contract deployed to Sepolia testnet.
// Update CONTRACT_ADDRESS if you redeploy.
export const CONTRACT_ADDRESS = "0x129f0E52Fe2825C6a05afD7631312D4A362ED61b";

// Your deployed AWS API Gateway base URL (Lambda + S3 backend).
export const API_BASE_URL = "https://8lntqytrt2.execute-api.ap-south-1.amazonaws.com";

export const SEPOLIA_CHAIN_ID = 11155111;
export const SEPOLIA_CHAIN_ID_HEX = "0xaa36a7";

// Matches contracts/DocumentVerification.sol
export const CONTRACT_ABI = [
  {
    inputs: [{ internalType: "bytes32", name: "hash", type: "bytes32" }],
    name: "uploadDocument",
    outputs: [],
    stateMutability: "nonpayable",
    type: "function",
  },
  {
    inputs: [{ internalType: "bytes32", name: "hash", type: "bytes32" }],
    name: "verifyDocument",
    outputs: [
      { internalType: "bool", name: "", type: "bool" },
      { internalType: "address", name: "", type: "address" },
      { internalType: "uint256", name: "", type: "uint256" },
    ],
    stateMutability: "view",
    type: "function",
  },
  {
    anonymous: false,
    inputs: [
      { indexed: true, internalType: "bytes32", name: "hash", type: "bytes32" },
      { indexed: true, internalType: "address", name: "owner", type: "address" },
      { indexed: false, internalType: "uint256", name: "timestamp", type: "uint256" },
    ],
    name: "DocumentUploaded",
    type: "event",
  },
];