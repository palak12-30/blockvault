# BlockVault Frontend

React + Vite frontend for the BlockVault document verification system.
Connects to the deployed Sepolia smart contract via MetaMask and ethers.js.

## What it does

- **Register panel**: hashes a file locally in your browser (keccak256, never
  uploads the actual file), then writes that fingerprint to the smart
  contract via your connected MetaMask wallet.
- **Verify panel**: hashes a file the same way, then reads the chain (via a
  public read-only RPC — no wallet needed) to check if that exact file was
  ever registered, and by whom.

## Setup

```bash
npm install
npm run dev
```

Then open the URL it prints (usually `http://localhost:5173`).

## Before you use it

- Make sure MetaMask is installed and set to the **Sepolia** test network.
- The contract address is already set in `src/lib/contract.js` to your
  deployed contract: `0x129f0E52Fe2825C6a05afD7631312D4A362ED61b`.
  If you ever redeploy the contract, update `CONTRACT_ADDRESS` there.

## Notes

- The Verify panel uses a public Sepolia RPC (`rpc.sepolia.org`) so anyone
  can verify a document without needing their own wallet or ETH — this
  matches real-world usage, where verification should be free and open.
- The Register panel requires a connected wallet with a small amount of
  Sepolia ETH for gas (same wallet you used to deploy the contract works
  fine, or connect a different one — either way it needs testnet ETH).
- Fraud detection integration point: not wired in yet. Once the AWS backend
  is live, the natural place to call it is right before `uploadDocument()`
  in `UploadPanel.jsx` — flag or block high-risk uploads before they're
  written on-chain.
