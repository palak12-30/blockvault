import "@nomiclabs/hardhat-ethers";
import { HardhatUserConfig } from "hardhat/config";

const config: HardhatUserConfig = {
  solidity: "0.8.28",
  networks: {
    sepolia: {
      url: "https://sepolia.infura.io/v3/b3d0be78610b4b30a6663c08bfe90eb0",
      accounts: ["7f1ab8af4f3cce7f9367ec8527a18bcc091aca1d60c39ec392d36c4845cc1e97"]
    }
  }
};

export default config;
