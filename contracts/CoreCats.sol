// SPDX-License-Identifier: MIT
pragma solidity ^0.8.28;

import {ERC721} from "@openzeppelin/contracts/token/ERC721/ERC721.sol";
import {Ownable} from "@openzeppelin/contracts/access/Ownable.sol";
import {ECDSA} from "@openzeppelin/contracts/utils/cryptography/ECDSA.sol";
import {MessageHashUtils} from "@openzeppelin/contracts/utils/cryptography/MessageHashUtils.sol";

interface ICoreCatsMetadataRenderer {
    function tokenURI(uint256 tokenId) external view returns (string memory);
}

contract CoreCats is ERC721, Ownable {
    uint256 public constant MAX_SUPPLY = 1000;
    uint256 public constant MAX_PER_ADDRESS = 3;

    // next token id (1-start or 0-start; here 1-start for readability)
    uint256 private _nextId = 1;

    // mint control
    mapping(address => uint256) public mintedPerAddress;
    mapping(bytes32 => bool) public usedNonce; // nonce uniqueness

    // EIP-191 typed message prefix: we sign a packed hash of (to, nonce, expiry, chainid, this)
    // signer is the contract owner (off-chain signer).
    address public signer; // optional: defaults to owner
    address public metadataRenderer;

    constructor() ERC721("CoreCats", "CCAT") Ownable(msg.sender) {
        signer = msg.sender;
    }

    function setSigner(address newSigner) external onlyOwner {
        signer = newSigner;
    }

    function setMetadataRenderer(address newRenderer) external onlyOwner {
        metadataRenderer = newRenderer;
    }

    function totalSupply() public view returns (uint256) {
        // since _nextId starts at 1
        return _nextId - 1;
    }

    function mint(
        address to,
        uint256 nonce,
        uint256 expiry,
        bytes calldata signature
    ) external {
        require(block.timestamp <= expiry, "signature expired");
        require(totalSupply() < MAX_SUPPLY, "sold out");
        require(mintedPerAddress[to] < MAX_PER_ADDRESS, "address mint limit");

        bytes32 message = _mintMessage(to, nonce, expiry);
        require(!usedNonce[message], "nonce used");
        usedNonce[message] = true;

        bytes32 digest = MessageHashUtils.toEthSignedMessageHash(message);
        address recovered = ECDSA.recover(digest, signature);

        require(recovered == signer, "invalid signature");

        uint256 tokenId = _nextId++;
        mintedPerAddress[to] += 1;
        _safeMint(to, tokenId);
    }

    function _mintMessage(
        address to,
        uint256 nonce,
        uint256 expiry
    ) internal view returns (bytes32) {
        // bind to chainId & contract address to prevent cross-chain and cross-contract replay
        return keccak256(abi.encodePacked(to, nonce, expiry, block.chainid, address(this)));
    }

    function tokenURI(uint256 tokenId) public view override returns (string memory) {
        _requireOwned(tokenId);
        require(metadataRenderer != address(0), "renderer not set");
        return ICoreCatsMetadataRenderer(metadataRenderer).tokenURI(tokenId);
    }
}
