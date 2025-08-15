// SPDX-License-Identifier: MIT
pragma solidity ^0.8.28;

import {ERC721} from "@openzeppelin/contracts/token/ERC721/ERC721.sol";
import {Ownable} from "@openzeppelin/contracts/access/Ownable.sol";
import {Strings} from "@openzeppelin/contracts/utils/Strings.sol";
import {Base64} from "@openzeppelin/contracts/utils/Base64.sol";
import {ECDSA} from "@openzeppelin/contracts/utils/cryptography/ECDSA.sol";
import {MessageHashUtils} from "@openzeppelin/contracts/utils/cryptography/MessageHashUtils.sol";

contract CoreCats is ERC721, Ownable {
    using Strings for uint256;

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

    constructor() ERC721("CoreCats", "CCAT") Ownable(msg.sender) {
        signer = msg.sender;
    }

    function setSigner(address newSigner) external onlyOwner {
        signer = newSigner;
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

    // Minimal on-chain SVG (24x24, fully transparent background, black silhouette placeholder)
    // You can later replace svgBody() with generated 24x24 cat pixels.
    function tokenURI(uint256 tokenId) public view override returns (string memory) {
        _requireOwned(tokenId);

        string memory name = string.concat("CoreCats #", tokenId.toString());
        string memory description = "CoreCats: fully on-chain 24x24 SVG cat.";
        string memory image = _svgImageData();

        bytes memory json = abi.encodePacked(
            '{"name":"', name,
            '","description":"', description,
            '","image":"', image,
            '","attributes":[]}'
        );

        return string.concat(
            "data:application/json;base64,",
            Base64.encode(json)
        );
    }

    function _svgImageData() internal pure returns (string memory) {
        // 24x24, transparent background, single black rect as placeholder.
        // Replace with the actual 24x24 pixel-art silhouette later.
        string memory svg =
            '<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24">'
            '<rect x="10" y="10" width="4" height="4" fill="#000000"/>'
            "</svg>";

        return string.concat(
            "data:image/svg+xml;base64,",
            Base64.encode(bytes(svg))
        );
    }
}
