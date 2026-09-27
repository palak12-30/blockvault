import { useState } from "react";
import { hashFile } from "../lib/hashFile";
import { API_BASE_URL } from "../lib/contract";
import HashDisplay from "./HashDisplay";

const STATUS = {
  IDLE: "idle",
  CHECKING: "checking",
  VERIFIED: "verified",
  NOT_FOUND: "not_found",
  ERROR: "error",
};

function formatTimestamp(unixSeconds) {
  return new Date(unixSeconds * 1000).toLocaleString();
}

export default function VerifyPanel() {
  const [file, setFile] = useState(null);
  const [hash, setHash] = useState(null);
  const [status, setStatus] = useState(STATUS.IDLE);
  const [errorMessage, setErrorMessage] = useState(null);
  const [record, setRecord] = useState(null);

  const handleFileChange = (e) => {
    const selected = e.target.files?.[0] || null;
    setFile(selected);
    setHash(null);
    setStatus(STATUS.IDLE);
    setErrorMessage(null);
    setRecord(null);
  };

  const handleVerify = async () => {
    if (!file) return;

    setErrorMessage(null);
    setRecord(null);

    try {
      setStatus(STATUS.CHECKING);
      const documentHash = await hashFile(file);
      setHash(documentHash);

      // Calls your own AWS backend (API Gateway -> Lambda -> Sepolia RPC)
      // instead of a public RPC directly from the browser — more reliable,
      // and this is the actual serverless pipeline this project is about.
      const response = await fetch(`${API_BASE_URL}/documents/${documentHash}`);

      if (!response.ok) {
        const errorBody = await response.json().catch(() => ({}));
        throw new Error(errorBody.error || `Backend returned ${response.status}`);
      }

      const data = await response.json();

      if (data.exists) {
        setRecord({ owner: data.owner, timestamp: data.timestamp });
        setStatus(STATUS.VERIFIED);
      } else {
        setStatus(STATUS.NOT_FOUND);
      }
    } catch (err) {
      setErrorMessage(err.message || "Something went wrong verifying this document.");
      setStatus(STATUS.ERROR);
    }
  };

  return (
    <section className="panel panel--verify">
      <div className="panel__header">
        <span className="panel__eyebrow">Verify</span>
        <h2 className="panel__title">Check a document's record</h2>
        <p className="panel__description">
          Upload the same file again to check whether it's been registered — no wallet
          connection required, this only reads from the chain.
        </p>
      </div>

      <label className="dropzone" htmlFor="verify-input">
        <input id="verify-input" type="file" onChange={handleFileChange} className="dropzone__input" />
        <span className="dropzone__icon" aria-hidden="true">⌕</span>
        <span className="dropzone__text">
          {file ? file.name : "Choose a file to verify"}
        </span>
      </label>

      {hash && <HashDisplay label="Document fingerprint (keccak256)" value={hash} />}

      <button className="btn btn--secondary btn--block" onClick={handleVerify} disabled={!file || status === STATUS.CHECKING}>
        {status === STATUS.CHECKING ? "Checking chain…" : "Verify document"}
      </button>

      {status === STATUS.VERIFIED && record && (
        <div className="result result--success">
          <p className="result__title">Verified on-chain</p>
          <dl className="result__meta">
            <dt>Registered by</dt>
            <dd><code>{record.owner}</code></dd>
            <dt>Registered on</dt>
            <dd>{formatTimestamp(record.timestamp)}</dd>
          </dl>
        </div>
      )}

      {status === STATUS.NOT_FOUND && (
        <div className="result result--neutral">
          <p className="result__title">No record found</p>
          <p className="result__body">
            This exact file has not been registered on-chain. Even a single-byte
            difference from the original produces a completely different fingerprint.
          </p>
        </div>
      )}

      {status === STATUS.ERROR && errorMessage && (
        <div className="result result--error">
          <p className="result__title">Verification failed</p>
          <p className="result__body">{errorMessage}</p>
        </div>
      )}
    </section>
  );
}
