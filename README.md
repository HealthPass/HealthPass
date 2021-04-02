# HealthPass

University of Arkansas Blockchain Hackathon 2021 Proof of Concept Smart Contract and example code.  Designed to meet all requirements of the Distributed Health Passport Use Case

## Requirements
* An Ethereum account on the Ropsten Network with at least 0.1 Eth
* ~~Infura API Key for interacting with the Ethereum network.~~  For ease of use, I have temporarily included an existing Infura API key.  Please don't abuse it and consider creating your own.
    1. Create a free account at https://infura.io/.  
    2. On the left select Ethereum and then Create New Project.
    3. Give it a name and submit. 
    4. On the next page, under KEYS, copy the PROJECT ID.
* Python3

## Installation - Windows
Download and install Python3.6 or higher from https://www.python.org/downloads/

Then from a command window run:
```
pip3 install -U web3
# OR
python3 -m pip install -U web3
```


## Installation - Ubuntu
From a clean Ubuntu install run the following commands to install the necessary packages and, optionally, the Solidity compiler and python bindings.
```
sudo apt install -y python3 python3-dev python3-pip
sudo pip3 install -U web3

# OPTIONAL, only necessary if wanting to compile yourself
sudo add-apt-repository ppa:ethereum/ethereum
sudo apt update
sudo apt install -y solc
sudo pip3 install -U py-solc py-evm py-solc-x solc-select

solc-select install 0.8.3
solc-select use 0.8.3
```


<br/>


## Configuration
| Key | Description  |  Default | Required? |
|------|------|------|------|
| INFURA_PROJECT_ID  | Infura Project ID | None | Yes |
| CONTRACT_OWNER_PRIVATE_KEY | Private key in hex format for the account that will be used to deploy the contract  | None  | Yes |
| ISSUER_PRIVATE_KEY  | If not supplied a new account will be generated and 0.05 Eth will be sent from the Owner's account.  The Issuer is the account performing most of the transactions.  | None |  No |
| PASSPORT_PRIVATE_KEY  | If not supplied a new account will be generated.  Only used for creating Passport identities, does not execute any transactions. | None  | No |
| CONTRACT_ADDRESS  | If you've already deployed a contract, set the address to use instead of deploying a new one  | None  | No |
| INFURA_API_URL  | Ropsten Infura API URL | wss://ropsten.infura.io/ws/v3/  | Yes |
| ETHERSCAN_URL  | Ropsten Etherscan URL  | https://ropsten.etherscan.io  | Yes |
| CONTRACT_FILEPATH  | Path to the Smart Contract .sol file  | HealthPass.sol  | Yes |
| ABI_FILEPATH  | Path to the precompiled Smart Contract ABI  | HealthPassABI.json  | No |
| BYTECODE_FILEPATH  | Path to the precompiled Smart Contract Bytecode  | HealthPassBytecode.json  | No |
| FORCE_COMPILE  | Whether to force a re-compile of the Smart Contract, only necessary if you've modified HealthPass.sol  | False | Yes |
| GAS_PRICE_STRATEGY  | Gas price strategy used for determining how much to pay for gas  | fast_gas_price_strategy  | Yes |
<br/>

## How To
Minimally, edit HealthPass.py and fill in values for INFURA_PROJECT_ID and CONTRACT_OWNER_PRIVATE_KEY and then run the script.
<br/>
<br/>
## Notes
In the real world the functionality in the script would be split between the contract Owner, Issuers and Verifiers
<br/>
<br/>
## Contributors
* Graham Brown
* Patrick Doyle
* Kevin Schoelz 
* Ian White
<br/>
<br/>
## License
Apache 2.0