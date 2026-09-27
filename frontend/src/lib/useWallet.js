import { useCallback, useEffect, useState } from "react";
import { ethers } from "ethers";
import { SEPOLIA_CHAIN_ID_HEX } from "./contract";

export function useWallet() {
  const [address, setAddress] = useState(null);
  const [provider, setProvider] = useState(null);
  const [chainId, setChainId] = useState(null);
  const [error, setError] = useState(null);
  const [connecting, setConnecting] = useState(false);

  const isMetaMaskInstalled = typeof window !== "undefined" && !!window.ethereum;

  const connect = useCallback(async () => {
    setError(null);

    if (!isMetaMaskInstalled) {
      setError("MetaMask not found. Install it from metamask.io to continue.");
      return;
    }

    setConnecting(true);
    try {
      const accounts = await window.ethereum.request({ method: "eth_requestAccounts" });
      const ethersProvider = new ethers.providers.Web3Provider(window.ethereum);
      const network = await ethersProvider.getNetwork();

      setProvider(ethersProvider);
      setAddress(accounts[0]);
      setChainId(network.chainId);
    } catch (err) {
      // 4001 = user rejected the connection request in MetaMask
      if (err.code === 4001) {
        setError("Connection request was rejected.");
      } else {
        setError(err.message || "Failed to connect wallet.");
      }
    } finally {
      setConnecting(false);
    }
  }, [isMetaMaskInstalled]);

  const switchToSepolia = useCallback(async () => {
    if (!isMetaMaskInstalled) return;
    try {
      await window.ethereum.request({
        method: "wallet_switchEthereumChain",
        params: [{ chainId: SEPOLIA_CHAIN_ID_HEX }],
      });
    } catch (err) {
      setError(err.message || "Failed to switch network.");
    }
  }, [isMetaMaskInstalled]);

  const disconnect = useCallback(() => {
    setAddress(null);
    setProvider(null);
    setChainId(null);
  }, []);

  // Keep state in sync if the user changes accounts or networks in MetaMask directly
  useEffect(() => {
    if (!isMetaMaskInstalled) return;

    const handleAccountsChanged = (accounts) => {
      if (accounts.length === 0) {
        disconnect();
      } else {
        setAddress(accounts[0]);
      }
    };

    const handleChainChanged = () => {
      // Reloading is the safest way to keep provider/network state consistent —
      // this is MetaMask's own recommended pattern for chain changes.
      window.location.reload();
    };

    window.ethereum.on("accountsChanged", handleAccountsChanged);
    window.ethereum.on("chainChanged", handleChainChanged);

    return () => {
      window.ethereum.removeListener("accountsChanged", handleAccountsChanged);
      window.ethereum.removeListener("chainChanged", handleChainChanged);
    };
  }, [isMetaMaskInstalled, disconnect]);

  return {
    address,
    provider,
    chainId,
    error,
    connecting,
    isMetaMaskInstalled,
    isCorrectNetwork: chainId === 11155111,
    connect,
    disconnect,
    switchToSepolia,
  };
}
