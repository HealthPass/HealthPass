// SPDX-License-Identifier: Apache-2.0

pragma solidity =0.8.3;

contract HealthPass {
    
    // the owner of the smart contract
    address public owner;
    
    // set the owner 
    constructor() {
        owner = msg.sender;
    }

    // modifier to restrict actions to just the owner
    modifier onlyOwner {
        require(msg.sender == owner);
        _;
    }

    // allow the owner to be changed, for example, to a governance or oversight body
    function changeOwner(address newOwner) public onlyOwner {
        emit OwnerChanged(owner, newOwner);            
        owner = newOwner;
    }

    // a mapping containing the authorized Issuer addresses
    mapping (address => bool) private authorizedIssuers;
    
    // used to restrict functions to only authorized issuers
    modifier onlyAuthorizedIssuers {
        require(authorizedIssuers[msg.sender]);
        _;
    }

    // representation of a User's HealthPass on the blockchain
    struct HealthPassport {

        // a json string containing key/value pairs of health information with the values being signed hashes
        // Name, Date of Birth, ID #, etc.
        string healthJson;

        // the address of the issuer that issued the credential
        address issuerAddress;      

        // a flag used to prevent issuers from being able to add credentials without the User's consent
        // will require that a User sign a credential before it can be added to their passport
        bool allowOnlySigned;

        // a list of hashes that are part of the credentials map
        bytes32[] credentialHashes;

        // bool used to track whether a particular passport exists
        bool isActive;
    }

    // a map of passport addresses to HealthPassports
    mapping (address => HealthPassport) private healthPassports;

    // a record representing a specific health event such as a vaccination, covid19 test, etc.
    struct Credential {

        // a json string containing key/value pairs of credential information with the values being signed hashes
        // Test/Vaccine Type, Issuer Name/Location, Date, Dose #, etc
        string credentialJson;

        // the address of the issuer that issued the credential
        address issuerAddress;
        
        // should be derivable from the public key, included for ease of use
        address passportAddress;

        // bool used to track whether a credential is valid
        bool isValid;
    }

    // key will be a hash of the credential itself
    mapping (bytes32 => Credential) private credentials;

    
    // authorize a new issuer to be able to create health passports and credentials
    function authorizeIssuer(string memory issuerName, address issuerAddress) public 

        // only the owner should be able to authorize new issuers
        onlyOwner {

            // for security reasons the owner should not be able to become an authorized issuer
            require(issuerAddress != owner);

            // add the issuer to the authorizedIssuers mappping
            authorizedIssuers[issuerAddress] = true;

            // emit the IssuerAuthorized event
            emit IssuerAuthorized(issuerName, issuerAddress);             
    }

    // return the passport at the given address
    function returnPassport(address passportAddr) public view returns(HealthPassport memory p) {
        return healthPassports[passportAddr];
    }

    // return the credential with the given hash
    function returnCredential(bytes32 credentialHash) public view returns(Credential memory p) {
        return credentials[credentialHash];
    }

    // create a health passport.  most of the processing will be done on the application side
    function createHealthPassport(string memory healthJson, address passportAddress, bool allowOnlySigned) public 

        // only authorized issuers can create new passports
        onlyAuthorizedIssuers {
            bytes32[] memory emptyCredentialsList;

            // create a health passport
            healthPassports[passportAddress] = HealthPassport({
                healthJson: healthJson,
                issuerAddress: msg.sender,
                allowOnlySigned: allowOnlySigned,
                credentialHashes: emptyCredentialsList,
                isActive: true                
            });

            // emit an event so that it is easier to track passports created by each Issuer 
            emit HealthPassportCreated(msg.sender, passportAddress);
    }

    // update a health passport.  the only information that is updatable is the health information and the allowOnlySigned bool; signedPassport is optional
    function updateHealthPassport(string memory healthJson, bool allowOnlySigned, address passportAddress, bytes memory signedPassport) public 

        // only authorized issuers can update health passports
        onlyAuthorizedIssuers {

            // the health passport must actually exist in order to be updated
            require(healthPassports[passportAddress].isActive);

            // locate the existing healthPassport
            HealthPassport storage healthPassport = healthPassports[passportAddress];

            // hash the provided values so that they can be compared against the hash that has been signed by the User
            bytes32 passportHash = keccak256(abi.encode(healthJson, allowOnlySigned));

            // if the passport currently has allowOnlySigned set to true, or if it is being updated to true, 
            //  check to make sure that the signedPassport signature is valid
            if (healthPassport.allowOnlySigned || allowOnlySigned) {

                // verify that the credential submitted in the transaction has not been altered since being signed by the User
                require(isSignatureValid(signedPassport, passportAddress, passportHash));  
            }

            // assign the new health information and value of allowOnlySigned
            healthPassport.healthJson = healthJson;     
            healthPassport.allowOnlySigned = allowOnlySigned;  

            emit HealthPassportUpdated(msg.sender, passportAddress);
    }

    
    // create a credential.  Can be a Covid19 test result, vaccination record, etc.  signedCredential is optional
    function createCredential(string memory credentialJson, address passportAddress, bytes memory signedCredentialJson) public 

        // only authorized issuers can create new credentials
        onlyAuthorizedIssuers {

            // hash the credential so that it can be compared against the hash that has been signed by the User
            bytes32 credentialHash = keccak256(abi.encode(credentialJson));

            // find the associated Health Passport
            HealthPassport storage healthPassport = healthPassports[passportAddress];

            // if the user requires that only credentials that they have approved can be added, 
            //  check to make sure that the signedCredential signature is valid
            if (healthPassport.allowOnlySigned) {

                // verify that the credential submitted in the transaction has not been altered since being signed by the User
                require(isSignatureValid(signedCredentialJson, passportAddress, credentialHash));  
            }
            
            // add the credential hash to the Passport's list of credentials
            healthPassport.credentialHashes.push(credentialHash);

            // create the credential and add it to the credentials map
            credentials[credentialHash] = Credential({
                credentialJson: credentialJson,
                issuerAddress: msg.sender,
                passportAddress: passportAddress,
                isValid: true
            });

            // emit an event so that it is easier to track credentials created by each Issuer
            emit CredentialCreated(msg.sender, passportAddress, credentialHash);
    }

    // the events
    event IssuerAuthorized(string issuerName, address issuerAddress);
    event HealthPassportCreated(address issuerAddress, address passportAddress);
    event HealthPassportUpdated(address issuerAddress, address passportAddress);
    event CredentialCreated(address issuerAddress, address passportAddress, bytes32 credentialHash);
    event OwnerChanged(address previousOwner, address newOwner);
    



    // not yet implemented
    // because the hash will change, this will require finding the existing credential, 
    //  deleting it and then recreating it
    function updateCredential() public {}


    // not yet implemented but will be used to validate whether a passport or credential that has been signed by a User has not been altered
    //  before being posted to the blockchain by an issuer
    function isSignatureValid(bytes memory signature, address signerAddress, bytes32 dataHash) private pure returns (bool) {
        return true;
    }



}