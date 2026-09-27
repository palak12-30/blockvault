import { useWallet } from "./lib/useWallet";
import WalletBar from "./components/WalletBar";
import UploadPanel from "./components/UploadPanel";
import VerifyPanel from "./components/VerifyPanel";
import "./App.css";

export default function App() {
  const wallet = useWallet();

  return (
    <div className="app">
      <WalletBar wallet={wallet} />

      <header className="hero">
        <span className="hero__eyebrow">Proof of existence, on-chain</span>
        <h1 className="hero__title">
          Every document leaves
          <br />
          an unforgeable mark.
        </h1>
        <p className="hero__subtitle">
          BlockVault fingerprints your files with keccak256 and stamps that fingerprint
          onto the Ethereum Sepolia testnet — permanent, tamper-evident, and verifiable by
          anyone, without ever uploading the file itself.
        </p>
      </header>

      <main className="panels">
        <UploadPanel wallet={wallet} />
        <VerifyPanel />
      </main>

      <footer className="footer">
        <p>
          Contract deployed on Sepolia testnet · Built with Solidity, ethers.js &amp; React
        </p>
      </footer>
    </div>
  );
}
