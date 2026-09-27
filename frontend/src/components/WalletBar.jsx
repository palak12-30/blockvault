function shortenAddress(addr) {
  return `${addr.slice(0, 6)}…${addr.slice(-4)}`;
}

export default function WalletBar({ wallet }) {
  const { address, connecting, error, isMetaMaskInstalled, isCorrectNetwork, connect, switchToSepolia } = wallet;

  return (
    <div className="wallet-bar">
      <div className="wallet-bar__brand">
        <span className="wallet-bar__seal" aria-hidden="true">◈</span>
        <span className="wallet-bar__name">BlockVault</span>
      </div>

      <div className="wallet-bar__status">
        {!isMetaMaskInstalled && (
          <a
            className="wallet-bar__install-link"
            href="https://metamask.io/download/"
            target="_blank"
            rel="noreferrer"
          >
            Install MetaMask
          </a>
        )}

        {isMetaMaskInstalled && !address && (
          <button className="btn btn--primary" onClick={connect} disabled={connecting}>
            {connecting ? "Connecting…" : "Connect wallet"}
          </button>
        )}

        {isMetaMaskInstalled && address && !isCorrectNetwork && (
          <button className="btn btn--warn" onClick={switchToSepolia}>
            Wrong network — switch to Sepolia
          </button>
        )}

        {isMetaMaskInstalled && address && isCorrectNetwork && (
          <div className="wallet-bar__connected">
            <span className="wallet-bar__dot" aria-hidden="true" />
            <span className="wallet-bar__address">{shortenAddress(address)}</span>
          </div>
        )}
      </div>

      {error && <p className="wallet-bar__error">{error}</p>}
    </div>
  );
}
