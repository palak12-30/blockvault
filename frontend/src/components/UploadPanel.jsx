import { useState } from "react";
import { ethers } from "ethers";
import { CONTRACT_ADDRESS, CONTRACT_ABI, API_BASE_URL } from "../lib/contract";
import { hashFile } from "../lib/hashFile";
import { fileToBase64 } from "../lib/fileToBase64";
import HashDisplay from "./HashDisplay";
import FraudBadge from "./FraudBadge";

const STATUS = {
  IDLE: "idle",
  HASHING: "hashing",
  CHECKING_FRAUD: "checking_fraud",
  AWAITING_SIGNATURE: "awaiting_signature",
  MINING: "mining",
  DONE: "done",
  ERROR: "error",
  ALREADY_EXISTS: "already_exists",
};

export default function UploadPanel({ wallet }) {
  const [file, setFile] = useState(null);
  const [hash, setHash] = useState(null);
  const [fraudAssessment, setFraudAssessment] = useState(null);
  const [status, setStatus] = useState(STATUS.IDLE);
  const [errorMessage, setErrorMessage] = useState(null);
  const [txHash, setTxHash] = useState(null);

  const canSubmit = wallet.address && wallet.isCorrectNetwork && file && status !== STATUS.MINING;

  const handleFileChange = (e) => {
    const selected = e.target.files?.[0] || null;
    setFile(selected);
    setHash(null);
    setFraudAssessment(null);
    setStatus(STATUS.IDLE);
    setErrorMessage(null);
    setTxHash(null);
  };

  const handleRegister = async () => {
    if (!file || !wallet.provider) return;

    setErrorMessage(null);
    setTxHash(null);
    setFraudAssessment(null);

    try {
      setStatus(STATUS.HASHING);
      const documentHash = await hashFile(file);
      setHash(documentHash);

      // Call the backend first: this stores a copy in S3 and runs fraud
      // scoring. This is informational only — a high risk score is shown
      // to the user but never blocks registration below.
      setStatus(STATUS.CHECKING_FRAUD);
      try {
        const base64 = await fileToBase64(file);
        const response = await fetch(`${API_BASE_URL}/documents`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            file_base64: base64,
            file_name: file.name,
            wallet_address: wallet.address,
          }),
        });

        if (response.ok) {
          const data = await response.json();
          setFraudAssessment(data.fraud_assessment);
        } else {
          setFraudAssessment({ error: "Backend returned an error" });
        }
      } catch (backendError) {
        // Backend/fraud check failing should never block registration —
        // degrade gracefully, same principle as the Lambda's own fallback.
        setFraudAssessment({ error: backendError.message });
      }

      const signer = wallet.provider.getSigner();
      const contract = new ethers.Contract(CONTRACT_ADDRESS, CONTRACT_ABI, signer);

      setStatus(STATUS.AWAITING_SIGNATURE);
      const tx = await contract.uploadDocument(documentHash);

      setStatus(STATUS.MINING);
      await tx.wait();

      setTxHash(tx.hash);
      setStatus(STATUS.DONE);
    } catch (err) {
      // 4001 = user rejected the signature in MetaMask
      if (err.code === 4001) {
        setErrorMessage("Transaction was rejected in MetaMask.");
        setStatus(STATUS.ERROR);
        return;
      }

      // Contract's require() message surfaces inside err.reason for ethers v5
      if (err.reason?.includes("already exists")) {
        setStatus(STATUS.ALREADY_EXISTS);
        return;
      }

      setErrorMessage(err.reason || err.message || "Something went wrong registering this document.");
      setStatus(STATUS.ERROR);
    }
  };

  return (
    <section className="panel">
      <div className="panel__header">
        <span className="panel__eyebrow">Register</span>
        <h2 className="panel__title">Stamp a document on-chain</h2>
        <p className="panel__description">
          Your file is hashed locally and screened for fraud risk before being
          written to the blockchain. A copy is stored securely; only the
          fingerprint (hash) ever goes on-chain.
        </p>
      </div>

      <label className="dropzone" htmlFor="upload-input">
        <input id="upload-input" type="file" onChange={handleFileChange} className="dropzone__input" />
        <span className="dropzone__icon" aria-hidden="true">⌁</span>
        <span className="dropzone__text">
          {file ? file.name : "Choose a file to register"}
        </span>
      </label>

      {hash && <HashDisplay label="Document fingerprint (keccak256)" value={hash} />}

      {fraudAssessment && <FraudBadge assessment={fraudAssessment} />}

      <button className="btn btn--primary btn--block" onClick={handleRegister} disabled={!canSubmit}>
        {status === STATUS.HASHING && "Hashing document…"}
        {status === STATUS.CHECKING_FRAUD && "Checking for fraud risk…"}
        {status === STATUS.AWAITING_SIGNATURE && "Confirm in MetaMask…"}
        {status === STATUS.MINING && "Registering on-chain…"}
        {(status === STATUS.IDLE || status === STATUS.DONE || status === STATUS.ERROR || status === STATUS.ALREADY_EXISTS) &&
          "Register document"}
      </button>

      {!wallet.address && (
        <p className="panel__hint">Connect your wallet to register a document.</p>
      )}
      {wallet.address && !wallet.isCorrectNetwork && (
        <p className="panel__hint panel__hint--warn">Switch to Sepolia testnet to continue.</p>
      )}

      {status === STATUS.DONE && (
        <div className="result result--success">
          <p className="result__title">Document registered</p>
          <p className="result__body">
            This fingerprint is now permanently on Sepolia. Anyone can verify this exact
            file later using the Verify panel.
          </p>
          <a
            className="result__link"
            href={`https://sepolia.etherscan.io/tx/${txHash}`}
            target="_blank"
            rel="noreferrer"
          >
            View transaction on Etherscan ↗
          </a>
        </div>
      )}

      {status === STATUS.ALREADY_EXISTS && (
        <div className="result result--warn">
          <p className="result__title">Already registered</p>
          <p className="result__body">
            This exact file has already been stamped on-chain before. Use the Verify panel
            to see who registered it and when.
          </p>
        </div>
      )}

      {status === STATUS.ERROR && errorMessage && (
        <div className="result result--error">
          <p className="result__title">Registration failed</p>
          <p className="result__body">{errorMessage}</p>
        </div>
      )}
    </section>
  );
}
