import json
import pprint
import os
import time
import binascii
from web3 import Web3
from web3.middleware import construct_sign_and_send_raw_middleware
from eth_account import Account
from eth_account.messages import encode_defunct
from web3.gas_strategies.time_based import fast_gas_price_strategy, medium_gas_price_strategy, slow_gas_price_strategy


class HealthPass(object):

    def __init__(self, contract_filepath=None, abi_filepath=None, bytecode_filepath=None, contract_address=None,
                 infura_api_url=None, infura_project_id=None, etherscan_url=None, timeout=300):

        # the path to the HealthPass contract
        self.contract_filepath = contract_filepath

        # the path to the HealthPass ABI
        self.abi_filepath = abi_filepath

        # the path to the HealthPass Bytecode
        self.bytecode_filepath = bytecode_filepath

        # optional; if the contract has already been deployed we can use that instead of deploying again
        self.contract_address = contract_address

        # the URL of the Infura API that will be used to interact with the ethereum network
        self.web3_endpoint_url = f'{infura_api_url}{infura_project_id}'

        # URL for etherscan
        self.etherscan_url = etherscan_url

        # the length of time to wait for transactions to complete
        self.timeout = timeout

        # these will be initialized later
        self.abi = None
        self.bytecode = None
        self.web3 = None
        self.contract = None

        # a list of the keys representing the HealthPassport struct in the Smart Contract
        self.HEALTH_PASSPORT_STRUCT = [
            'healthJson',
            'issuerAddress',
            'allowOnlySigned',
            'credentialHashes',
            'isActive'
        ]

        # a list of the keys representing the Credential struct in the Smart Contract
        self.CREDENTIAL_STRUCT = [
            'credentialJson',
            'issuerAddress',
            'passportAddress',
            'isValid'
        ]
    
    # initialize the web3 object using the supplied account and price strategy
    def initialize_web3(self, account, price_strategy=None):

        # initialize the websocket Infura endpoint
        self.web3 = Web3(Web3.WebsocketProvider(self.web3_endpoint_url))

        # use this account to sign all web3 transactions
        self.web3.middleware_onion.add(construct_sign_and_send_raw_middleware(account))

        # set the account as the default account
        self.web3.eth.default_account = account.address

        self.web3.eth.setGasPriceStrategy(price_strategy)

    # initialize the contract, either by deploying a new contract or by providing
    #  the address of a contract that was previously deployed
    def initialize_contract(self, force_compile=False):

        # first check if the abi and bytecode already exist
        if os.path.exists(self.abi_filepath) and os.path.exists(self.bytecode_filepath) and not force_compile:

            # if they do exist, load them from file
            with open(self.abi_filepath) as f:
                self.abi = json.load(f)

            with open(self.bytecode_filepath) as f:
                self.bytecode = json.load(f)
        else:
            self.compile_contract()

        # if we have the address we just need to initialize it
        if self.contract_address:

            print('contract address provided, initializing...')
            self.contract = self.web3.eth.contract(address=self.contract_address, abi=self.abi)

        else:
            # if we dont have the contract address then we need to deploy it
            self.deploy_contract()
            print('new contract initialized')

            # sometimes there is a delay after deploying a contract so we
            #  need to wait until its for sure available
            code = health_pass.web3.eth.getCode(health_pass.contract_address)
            while code in ['0x', '0x0']:
                print('contract not found? waiting...')
                time.sleep(1)

    # compile the contract using solc
    def compile_contract(self):
        print(f'compiling contract at {self.contract_filepath}')

        # load the contract source code from file
        with open(self.contract_filepath, 'r') as f:
            contract_content = f.read()

        from solc import compile_standard

        # compile the contract source code
        compiled_sol = compile_standard({
         "language": "Solidity",
         "sources": {
             "HealthPass.sol": {
                 "content": contract_content
             }
         },
         "settings":
             {
                 "outputSelection": {
                     "*": {
                         "*": [
                             "metadata", "evm.bytecode", "evm.bytecode.sourceMap"
                         ]
                     }
                 }
             }
        })

        # the contract ABI, used by web3 to interact with the contract
        self.abi = json.loads(compiled_sol['contracts']['HealthPass.sol']['HealthPass']['metadata'])['output']['abi']

        # the compiled bytecode, used for deploying the contract
        self.bytecode = compiled_sol['contracts']['HealthPass.sol']['HealthPass']['evm']['bytecode']['object']

        # save the ABI and bytecode to file so that it can be re-used
        with open(self.abi_filepath, 'w') as f:
            json.dump(self.abi, f)

        with open(self.bytecode_filepath, 'w') as f:
            json.dump(self.bytecode, f)

    # deploy the contract to the blockchain
    def deploy_contract(self):

        print('deploying contract')

        # initialize the contract
        self.contract = self.web3.eth.contract(abi=self.abi, bytecode=self.bytecode)

        # Submit the transaction that deploys the contract
        tx_hash = self.contract.constructor().transact()
        print(f'Contract transaction URL: {self.etherscan_url}/tx/0x{binascii.hexlify(tx_hash).decode()}')

        # Wait for the transaction to be mined, and get the transaction receipt
        tx_receipt = self.web3.eth.waitForTransactionReceipt(tx_hash, timeout=self.timeout)

        self.contract_address = tx_receipt.contractAddress

        print(f'Contract URL: {self.etherscan_url}/address/{tx_receipt.contractAddress}')
        print(f'Transaction Cost: {self.calculate_transaction_cost(tx_receipt)} Eth')

        # after deploying the contract, do a quick test to check the owner

        # re-initialize the contract using the new address
        self.contract = self.web3.eth.contract(address=tx_receipt.contractAddress, abi=self.abi)

        # get the value of the 'owner' variable
        # contract_owner_address = self.contract.functions.owner().call()
        # print("Contract Owner's Address: ", contract_owner_address)

    # authorize an Issuer account to be able to create HealthPasses and Credentials
    def authorize_issuer(self, issuer_name, issuer_account):

        print(f'Authorizing {issuer_name} ({issuer_account.address}) as Issuer')

        # call the authorizeIssuer smart contract function
        tx_hash = self.contract.functions.authorizeIssuer(issuer_name, issuer_account.address).transact()

        print(f'Authorize Issuer transaction URL: {self.etherscan_url}/tx/0x{binascii.hexlify(tx_hash).decode()}')

        tx_receipt = self.web3.eth.waitForTransactionReceipt(tx_hash, timeout=self.timeout)
        print(f'{issuer_name} authorized!')
        print(f'Transaction Cost: {self.calculate_transaction_cost(tx_receipt)} Eth')

    # create a HealthPass
    def create_health_passport(self, health_dict, issuer_account, passport_account):

        # for each piece of health data, replace the plain text value with the signed data
        hashed_dict = {k: self.sign_data(v, issuer_account) for k, v in health_dict.items()}

        # turn the health data into a json string
        json_string = json.dumps(hashed_dict)

        # call the createHealthPassport() Smart Contract function 
        tx_hash = self.contract.functions.createHealthPassport(json_string, passport_account.address,
                                                               allow_only_signed).transact()
        print(f'Create Health Passport transaction URL: {self.etherscan_url}/tx/0x{binascii.hexlify(tx_hash).decode()}')

        # wait for the transaction to complete and print the cost
        tx_receipt = self.web3.eth.waitForTransactionReceipt(tx_hash, timeout=self.timeout)
        print(f'Health Passport {passport_account.address} created!')
        print(f'Transaction Cost: {self.calculate_transaction_cost(tx_receipt)} Eth')

    # create a Credential
    def create_credential(self, credential_dict, issuer_account, passport_account):

        # for each piece of credential data, replace the plain text value with the signed data
        hashed_dict = {k: self.sign_data(v, issuer_account) for k, v in credential_dict.items()}

        # turn the credential data into a json string
        json_string = json.dumps(hashed_dict)

        # call the createCredential() Smart Contract function 
        tx_hash = self.contract.functions.createCredential(json_string, passport_account.address, b'').transact()
        print(f'Create Health Passport transaction URL: {self.etherscan_url}/tx/0x{binascii.hexlify(tx_hash).decode()}')
        
        # wait for the transaction to complete and print the cost
        tx_receipt = self.web3.eth.waitForTransactionReceipt(tx_hash, timeout=self.timeout)
        print(f'Credential created for passport {passport_account.address}!')
        print(f'Transaction Cost: {self.calculate_transaction_cost(tx_receipt)} Eth')

    # query the Smart Contract for the specified passport
    def get_health_passport(self, passport_address):

        # use the returnPassport view function to return the passport at the given address
        health_passport_values = health_pass.contract.functions.returnPassport(passport_address).call()

        # health_passport_values is returned as a list, combine that with the passport 'struct' to create a dict
        health_passport_dict = dict(zip(self.HEALTH_PASSPORT_STRUCT, health_passport_values))

        # convert the json string into a dict
        health_passport_dict['healthJson'] = json.loads(health_passport_dict['healthJson'])

        return health_passport_dict

    # query the Smart Contract for the specified credential
    def get_credential(self, credential_hash):

        # use the returnCredential view function to return the credential with the given hash
        credential_values = health_pass.contract.functions.returnCredential(credential_hash).call()

        # credential_values is returned as a list, combine that with the credential 'struct' to create a dict
        credential_dict = dict(zip(self.CREDENTIAL_STRUCT, credential_values))

        # convert the json string into a dict
        credential_dict['credentialJson'] = json.loads(credential_dict['credentialJson'])

        return credential_dict

    # calculate the Eth cost of a given transaction
    def calculate_transaction_cost(self, tx_receipt):

        # returned in wei
        gas_price = self.web3.eth.getTransaction(tx_receipt.transactionHash).gasPrice

        # total wei spent
        wei_cost = tx_receipt.gasUsed * gas_price

        # total eth spent
        eth_cost = self.web3.fromWei(wei_cost, 'ether')

        return eth_cost

    # create a signature from a given piece of data
    def sign_data(self, data, signing_account):

        # create a eip191 encoded message
        message = encode_defunct(text=data)

        # sign the message using the provided account's private key
        signed_message = self.web3.eth.account.sign_message(message, private_key=signing_account.privateKey)
        return signed_message.signature.hex()

    # validate the signature of a piece of data
    def validate_signature(self, data, signature, signer_address):

        # create a eip191 encoded message
        message = encode_defunct(text=data)

        # using fancy math, take the message and the signature and output an account address
        address = self.web3.eth.account.recover_message(message, signature=signature)

        # hopefully its the address of the account that signed it!
        if signer_address == address:
            return True
        else:
            return False

    # validate all key/signature and key/plaintext data in a given set of dictionaries
    def validate_data_dict(self, plaintext_dict, signature_dict, signer_address):

        # for each key/signature pair in the dictionary check if the signature and plain text data match
        for key, data_signature in signature_dict.items():

            is_valid = self.validate_signature(plaintext_dict[key], data_signature, signer_address)

            if not is_valid:
                print(f'WARNING!!!  User plain text health data for {key} does not match signature!')
                return False
        return True

    #######################################################################################
    # The below are utility functions that aren't necessarily required for the HealthPass
    #######################################################################################

    # transfer eth from one address to another
    def transfer_eth(self, from_address, to_address, amount, gas_price=None, gas_amount=None):

        # build the transaction
        transaction = {
            'from': from_address,
            'to': to_address,
            'value': self.web3.toWei(amount, "ether"),
            'chainId': 3,   # 3 is the chain id for Ropsten
            'nonce': self.web3.eth.getTransactionCount(from_address)
        }

        # can optionally specify a gas price and amount
        if gas_price:
            transaction['gasPrice'] = gas_price

        if gas_amount:
            transaction['gas'] = gas_amount

        # send the transactions and print the details
        tx_hash = self.web3.eth.send_transaction(transaction)
        print(f'Sent {amount} Eth from {from_address} to {to_address}!')
        print(f'Transaction URL: {self.etherscan_url}/tx/0x{binascii.hexlify(tx_hash).decode()}')

    # get the account balance of the provided address and convert it to eth
    def get_account_balance(self, account_address):
        return self.web3.fromWei(self.web3.eth.get_balance(account_address), 'ether')

    # send the entire account balance from one address to another
    def send_account_balance(self, from_address, to_address):

        # check how much eth we currently have
        account_balance = self.web3.eth.get_balance(from_address)

        # if we don't have any Eth to send, return
        if account_balance == 0:
            print('No eth to send!')
            return

        # generate a gas price so we'll know how much we're paying
        gas_price = self.web3.eth.generateGasPrice()

        # need to calculate how much its going to take to transfer the Eth and then send what's left
        # 21000 is the set amount of gas needed to transfer Eth
        balance_minus_gas = self.web3.fromWei(account_balance - (21000 * gas_price), 'ether')

        self.transfer_eth(from_address, to_address, balance_minus_gas, gas_price=gas_price, gas_amount=21000)

# initialize an account object using a private key
def initialize_account(private_key):

    # when the private key is copied directly from metamask it doesn't include
    #  the 0x in front so make sure its there
    if not private_key.startswith('0x'):
        private_key = '0x' + private_key

    return Account.privateKeyToAccount(private_key)

# create a new private key; not recommended to use this for anything important
def create_new_account():
    return Web3().eth.account.create()



# CONFIGURATION
########################################################################################

# please don't abuse this!
INFURA_PROJECT_ID = '1a7577ceeb01411dbb20012cea2c3316'

# the private key of the account that will be used to deploy the contract
# Note: The account must have at least ~0.1 Eth for everything to work!
CONTRACT_OWNER_PRIVATE_KEY = ''

# if you have previously deployed this contract and want to use that instead of deploying a new one
#  set the contract address here
CONTRACT_ADDRESS = ''

# Optional; the private key of the 'Issuer' account that represents healthcare providers such as Hospitals or Clinics
# Must have at least 0.05 Eth in order to create new passports and credentials
# If not provided, a new account will be created and given a small amount of eth from the Owner account
ISSUER_PRIVATE_KEY = ''

# Optional; the private key of a User's Health Passport
# Since the User does not interact with the blockchain, no Eth is required
# If not provided, a new account will be created
PASSPORT_PRIVATE_KEY = ''

# base URL for the Infura Ropsten API
INFURA_API_URL = 'wss://ropsten.infura.io/ws/v3/'

# base URL for the Ropsten etherscan website
ETHERSCAN_URL = 'https://ropsten.etherscan.io'

# the path to the contract and precompiled ABI and Bytecode of the contract
CONTRACT_FILEPATH = 'HealthPass.sol'
ABI_FILEPATH = 'HealthPassABI.json'
BYTECODE_FILEPATH = 'HealthPassBytecode.json'

# by default, we will attempt to use the precompiled ABI and Bytecode but if you modify the contract
#  and need to re-compile it, set this to True
# Note that compiling only works on Linux
FORCE_COMPILE = False

# the default price strategy used to determine how much to pay for gas when making transactions
#  calculates this based on the prices used in the previous block
# fast aims to complete within 1 minute, medium within 10 minutes and slow within 1 hour
# during my testing the difference in gas price between strategies was <5%
GAS_PRICE_STRATEGY = fast_gas_price_strategy
########################################################################################

# only execute if this script is called directly
if __name__ == '__main__':
    
    print('starting!')

    # initialize an instance of the HealthPass class
    health_pass = HealthPass(contract_filepath=CONTRACT_FILEPATH,
                             abi_filepath=ABI_FILEPATH,
                             bytecode_filepath=BYTECODE_FILEPATH,
                             contract_address=CONTRACT_ADDRESS,
                             infura_api_url=INFURA_API_URL,
                             infura_project_id=INFURA_PROJECT_ID,
                             etherscan_url=ETHERSCAN_URL)

    # initialize the contract owner's account
    contract_owner_account = initialize_account(CONTRACT_OWNER_PRIVATE_KEY)

    # initialize the web3 endpoint as the owner account and set the price strategy
    health_pass.initialize_web3(contract_owner_account, price_strategy=GAS_PRICE_STRATEGY)

    # check the balance of the contract owner's account to ensure it has enough
    contract_owner_balance = health_pass.get_account_balance(contract_owner_account.address)
    if contract_owner_balance < 0.1:
        print(f'\n\nWARNING! Contract Owner Account only has {contract_owner_balance} Eth '
              f'which may not be enough for contract deployment and interaction!\n\n')

    if not ISSUER_PRIVATE_KEY:
        print('Issuer private key not provided, generating a new one and transferring some Eth')
        issuer_account = create_new_account()

        health_pass.transfer_eth(contract_owner_account.address, issuer_account.address, 0.05)
        recover_eth = True
    else:
        issuer_account = initialize_account(ISSUER_PRIVATE_KEY)
        recover_eth = False

    if not PASSPORT_PRIVATE_KEY:
        print('Passport private key not provided, generating a new one')
        passport_account = create_new_account()
    else:
        passport_account = initialize_account(PASSPORT_PRIVATE_KEY)

    # in case something goes wrong after this, wrap it in a try/catch so that
    #  if we had sent Eth to the issuer account we can send it back to the owner account
    try:
        # initialize the HealthPass Smart Contract
        health_pass.initialize_contract(force_compile=FORCE_COMPILE)

        print('\nSetup Complete!\n')

        # Still using the Owner's account, authorize the Issuer account
        #  so that they can create HealthPasses and Credentials
        health_pass.authorize_issuer('Pat Walker Health Center', issuer_account)

        #########################################################################
        # These are the actions that an Issuer would perform
        #########################################################################

        # after authorizing the issuer we need to switch accounts to the issuer account that was just authorized
        # we also need to re-initialize the contract for it to work correctly under the new account
        health_pass.initialize_web3(issuer_account, price_strategy=GAS_PRICE_STRATEGY)
        health_pass.initialize_contract()

        health_data = {
            'First Name': 'John',
            'Last Name': 'Smith',
            'Date of Birth': '10/5/1970'
        }
        health_pass.create_health_passport(health_data, issuer_account, passport_account)

        credential_data = {
            'Vaccine Type': 'Moderna',
            'Date': '4/1/2021',
            'Dose #': '1'
        }

        health_pass.create_credential(credential_data, issuer_account, passport_account)

        #########################################################################
        #########################################################################

        #########################################################################
        # These are the actions that a Verifier would perform
        #########################################################################

        # get the passport at the provided address
        # in a real world scenario the address would be encoded by a User's HealthPass app
        #  into a QR code and presented to the Verifier
        passport_dict = health_pass.get_health_passport(passport_account.address)
        pprint.pprint(passport_dict)

        # get the credential at the provided address
        # in a real world scenario the address would be encoded by a User's HealthPass app
        #  into a QR code and presented to the Verifier
        credential_dict = health_pass.get_credential(passport_dict['credentialHashes'][0])
        pprint.pprint(credential_dict)

        # in a real world scenario the health and credential information would have been
        #  included in the QR code as well, so that the Verifier can compare the signatures
        #  on the blockchain to the plain text values provided by the User

        # for each piece of health information in the Health Passport, verify that the signature matches
        #  what the User sent over as plain text
        passport_valid = health_pass.validate_data_dict(health_data, passport_dict['healthJson'],
                                                        passport_dict['issuerAddress'])

        # for each piece of health information in the Credential, verify that the signature matches
        #  what the User sent over as plain text
        credential_valid = health_pass.validate_data_dict(credential_data, credential_dict['credentialJson'],
                                                          credential_dict['issuerAddress'])

        if not passport_valid or not credential_valid:
            print('\n\nUser Passport or Credential Invalid! Deny entry!\n\n')
        else:
            print('\n\nUser Passport and Credential valid! Access granted!\n\n')
        
        #########################################################################
        #########################################################################

    except Exception as e:
        print(e)

    if recover_eth:
        health_pass.send_account_balance(issuer_account.address, contract_owner_account.address)

    print('done!')

