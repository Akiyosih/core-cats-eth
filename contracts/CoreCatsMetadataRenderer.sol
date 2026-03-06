// SPDX-License-Identifier: MIT
pragma solidity ^0.8.28;

import {Strings} from "@openzeppelin/contracts/utils/Strings.sol";
import {Base64} from "@openzeppelin/contracts/utils/Base64.sol";

interface ICoreCatsOnchainData {
    function tokenRecords() external pure returns (bytes memory);
    function colorTupleMeta() external pure returns (bytes memory);
    function colorTupleColors() external pure returns (bytes memory);
    function patternSlotCounts() external pure returns (bytes memory);
    function patternMasks() external pure returns (bytes memory);
    function fixedLayerPixels() external pure returns (bytes memory);
    function fixedLayerPaletteMeta() external pure returns (bytes memory);
    function fixedLayerPalettes() external pure returns (bytes memory);
}

contract CoreCatsMetadataRenderer {
    using Strings for uint256;

    uint256 public constant MAX_SUPPLY = 1000;

    // pattern ids
    uint8 private constant PATTERN_SUPERRARE = 10;

    // collar type ids
    uint8 private constant COLLAR_NONE = 0;
    uint8 private constant COLLAR_CHECKERED = 1;
    uint8 private constant COLLAR_CLASSIC_RED = 2;

    // rarity tier ids
    uint8 private constant RARITY_COMMON = 0;
    uint8 private constant RARITY_RARE = 1;
    uint8 private constant RARITY_SUPERRARE = 2;

    // rarity type ids
    uint8 private constant RARITY_TYPE_NONE = 0;
    uint8 private constant RARITY_TYPE_ODD_EYES = 1;
    uint8 private constant RARITY_TYPE_RED_NOSE = 2;
    uint8 private constant RARITY_TYPE_BLUE_NOSE = 3;
    uint8 private constant RARITY_TYPE_GLASSES = 4;
    uint8 private constant RARITY_TYPE_SUNGLASSES = 5;
    uint8 private constant RARITY_TYPE_CORELOGO = 6;
    uint8 private constant RARITY_TYPE_PINGLOGO = 7;

    // fixed layer ids in CoreCatsOnchainData
    uint8 private constant LAYER_BASE = 0;
    uint8 private constant LAYER_COLLAR_CHECKERED = 1;
    uint8 private constant LAYER_COLLAR_CLASSIC_RED = 2;
    uint8 private constant LAYER_RARE_ODD_EYES = 3;
    uint8 private constant LAYER_RARE_RED_NOSE = 4;
    uint8 private constant LAYER_RARE_BLUE_NOSE = 5;
    uint8 private constant LAYER_RARE_GLASSES = 6;
    uint8 private constant LAYER_RARE_SUNGLASSES = 7;
    uint8 private constant LAYER_SUPERRARE_CORE = 8;
    uint8 private constant LAYER_SUPERRARE_PING = 9;

    ICoreCatsOnchainData public immutable data;

    struct DataBundle {
        bytes tokenRecords;
        bytes colorTupleMeta;
        bytes colorTupleColors;
        bytes patternSlotCounts;
        bytes patternMasks;
        bytes fixedLayerPixels;
        bytes fixedLayerPaletteMeta;
        bytes fixedLayerPalettes;
    }

    struct TokenRecord {
        uint8 patternId;
        uint8 paletteId;
        uint8 collarTypeId;
        uint8 rarityTierId;
        uint8 rarityTypeId;
        uint16 colorTupleIndex;
    }

    constructor(address dataAddress) {
        require(dataAddress != address(0), "data address is zero");
        data = ICoreCatsOnchainData(dataAddress);
    }

    function tokenURI(uint256 tokenId) external view returns (string memory) {
        require(tokenId >= 1 && tokenId <= MAX_SUPPLY, "token out of range");

        DataBundle memory d = _loadData();
        TokenRecord memory rec = _decodeTokenRecord(d.tokenRecords, tokenId);

        string memory image = _buildImageData(d, rec);
        string memory attributes = _buildAttributes(rec);
        string memory name = string.concat("CoreCats #", tokenId.toString());
        string memory description = "CoreCats fully on-chain 24x24 SVG.";

        bytes memory json = abi.encodePacked(
            '{"name":"',
            name,
            '","description":"',
            description,
            '","image":"',
            image,
            '","attributes":',
            attributes,
            "}"
        );

        return string.concat("data:application/json;base64,", Base64.encode(json));
    }

    function _loadData() internal view returns (DataBundle memory d) {
        d.tokenRecords = data.tokenRecords();
        d.colorTupleMeta = data.colorTupleMeta();
        d.colorTupleColors = data.colorTupleColors();
        d.patternSlotCounts = data.patternSlotCounts();
        d.patternMasks = data.patternMasks();
        d.fixedLayerPixels = data.fixedLayerPixels();
        d.fixedLayerPaletteMeta = data.fixedLayerPaletteMeta();
        d.fixedLayerPalettes = data.fixedLayerPalettes();
    }

    function _decodeTokenRecord(bytes memory tokenRecords, uint256 tokenId) internal pure returns (TokenRecord memory rec) {
        uint256 off = (tokenId - 1) * 4;
        uint32 packed = uint32(uint8(tokenRecords[off]))
            | (uint32(uint8(tokenRecords[off + 1])) << 8)
            | (uint32(uint8(tokenRecords[off + 2])) << 16)
            | (uint32(uint8(tokenRecords[off + 3])) << 24);

        rec.patternId = uint8(packed & 0xF);
        rec.paletteId = uint8((packed >> 4) & 0xF);
        rec.collarTypeId = uint8((packed >> 8) & 0x3);
        rec.rarityTierId = uint8((packed >> 10) & 0x3);
        rec.rarityTypeId = uint8((packed >> 12) & 0xF);
        rec.colorTupleIndex = uint16((packed >> 16) & 0x1FF);
    }

    function _buildImageData(DataBundle memory d, TokenRecord memory rec) internal pure returns (string memory) {
        string memory body = "";

        if (rec.rarityTierId == RARITY_SUPERRARE) {
            uint8 layerId = rec.rarityTypeId == RARITY_TYPE_CORELOGO ? LAYER_SUPERRARE_CORE : LAYER_SUPERRARE_PING;
            body = _renderFixedLayer(d, layerId, body);
        } else {
            body = _renderPatternLayer(d, rec, body);
            body = _renderFixedLayer(d, LAYER_BASE, body);

            if (rec.collarTypeId == COLLAR_CHECKERED) {
                body = _renderFixedLayer(d, LAYER_COLLAR_CHECKERED, body);
            } else if (rec.collarTypeId == COLLAR_CLASSIC_RED) {
                body = _renderFixedLayer(d, LAYER_COLLAR_CLASSIC_RED, body);
            }

            if (rec.rarityTierId == RARITY_RARE) {
                uint8 rareLayer = _rareLayerId(rec.rarityTypeId);
                if (rareLayer != 255) {
                    body = _renderFixedLayer(d, rareLayer, body);
                }
            }
        }

        string memory svg = string.concat(
            '<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" shape-rendering="crispEdges">',
            body,
            "</svg>"
        );

        return string.concat("data:image/svg+xml;base64,", Base64.encode(bytes(svg)));
    }

    function _renderPatternLayer(DataBundle memory d, TokenRecord memory rec, string memory svg)
        internal
        pure
        returns (string memory)
    {
        if (rec.patternId == PATTERN_SUPERRARE) {
            return svg;
        }

        (uint16 tupleOffset, uint8 tupleLen) = _tupleMeta(d.colorTupleMeta, rec.colorTupleIndex);
        uint8 slotCount = uint8(d.patternSlotCounts[rec.patternId]);
        require(tupleLen >= slotCount, "tuple/slot mismatch");

        uint256 patternPixelStart = uint256(rec.patternId) * 576;

        for (uint8 y = 0; y < 24; y++) {
            uint8 x = 0;
            while (x < 24) {
                uint8 pix = _nibbleAt(d.patternMasks, patternPixelStart + uint256(y) * 24 + x);
                if (pix == 0) {
                    unchecked {
                        x++;
                    }
                    continue;
                }

                uint8 start = x;
                while (x < 24) {
                    uint8 cur = _nibbleAt(d.patternMasks, patternPixelStart + uint256(y) * 24 + x);
                    if (cur != pix) {
                        break;
                    }
                    unchecked {
                        x++;
                    }
                }

                bytes3 color = _rgbAt(d.colorTupleColors, tupleOffset + uint16(pix - 1));
                svg = _appendRect(svg, start, y, x - start, color);
            }
        }

        return svg;
    }

    function _renderFixedLayer(DataBundle memory d, uint8 layerId, string memory svg)
        internal
        pure
        returns (string memory)
    {
        (uint16 paletteOffset, uint8 paletteCount) = _fixedLayerPaletteMeta(d.fixedLayerPaletteMeta, layerId);
        if (paletteCount == 0) {
            return svg;
        }

        uint256 pixelStart = uint256(layerId) * 576;

        for (uint8 y = 0; y < 24; y++) {
            uint8 x = 0;
            while (x < 24) {
                uint8 pix = _nibbleAt(d.fixedLayerPixels, pixelStart + uint256(y) * 24 + x);
                if (pix == 0) {
                    unchecked {
                        x++;
                    }
                    continue;
                }

                uint8 start = x;
                while (x < 24) {
                    uint8 cur = _nibbleAt(d.fixedLayerPixels, pixelStart + uint256(y) * 24 + x);
                    if (cur != pix) {
                        break;
                    }
                    unchecked {
                        x++;
                    }
                }

                bytes3 color = _rgbAt(d.fixedLayerPalettes, paletteOffset + uint16(pix - 1));
                svg = _appendRect(svg, start, y, x - start, color);
            }
        }

        return svg;
    }

    function _buildAttributes(TokenRecord memory rec) internal pure returns (string memory) {
        string memory pattern = _patternName(rec.patternId);
        string memory palette = _paletteName(rec.paletteId);
        string memory collar = rec.collarTypeId == COLLAR_NONE ? "without_collar" : "with_collar";
        string memory collarType = _collarTypeName(rec.collarTypeId);
        string memory tier = _rarityTierName(rec.rarityTierId);
        string memory rtype = _rarityTypeName(rec.rarityTypeId);

        return string.concat(
            '[{"trait_type":"Pattern","value":"',
            pattern,
            '"},{"trait_type":"Color Variation","value":"',
            palette,
            '"},{"trait_type":"Collar","value":"',
            collar,
            '"},{"trait_type":"Collar Type","value":"',
            collarType,
            '"},{"trait_type":"Rarity Tier","value":"',
            tier,
            '"},{"trait_type":"Rarity Type","value":"',
            rtype,
            '"}]'
        );
    }

    function _tupleMeta(bytes memory meta, uint16 tupleIndex) internal pure returns (uint16 offset, uint8 len) {
        uint256 pos = uint256(tupleIndex) * 3;
        offset = (uint16(uint8(meta[pos])) << 8) | uint16(uint8(meta[pos + 1]));
        len = uint8(meta[pos + 2]);
    }

    function _fixedLayerPaletteMeta(bytes memory meta, uint8 layerId) internal pure returns (uint16 offset, uint8 len) {
        uint256 pos = uint256(layerId) * 3;
        offset = (uint16(uint8(meta[pos])) << 8) | uint16(uint8(meta[pos + 1]));
        len = uint8(meta[pos + 2]);
    }

    function _nibbleAt(bytes memory packed, uint256 index) internal pure returns (uint8) {
        uint8 b = uint8(packed[index >> 1]);
        if ((index & 1) == 0) {
            return b >> 4;
        }
        return b & 0x0F;
    }

    function _rgbAt(bytes memory rgbTriples, uint16 colorIndex) internal pure returns (bytes3) {
        uint256 off = uint256(colorIndex) * 3;
        return bytes3((uint24(uint8(rgbTriples[off])) << 16) | (uint24(uint8(rgbTriples[off + 1])) << 8) | uint24(uint8(rgbTriples[off + 2])));
    }

    function _appendRect(string memory svg, uint8 x, uint8 y, uint8 w, bytes3 color)
        internal
        pure
        returns (string memory)
    {
        return string.concat(
            svg,
            '<rect x="',
            uint256(x).toString(),
            '" y="',
            uint256(y).toString(),
            '" width="',
            uint256(w).toString(),
            '" height="1" fill="',
            _hexColor(color),
            '"/>'
        );
    }

    function _hexColor(bytes3 color) internal pure returns (string memory) {
        uint24 v = uint24(color);
        bytes memory s = new bytes(7);
        s[0] = "#";
        s[1] = _hexNibble((v >> 20) & 0xF);
        s[2] = _hexNibble((v >> 16) & 0xF);
        s[3] = _hexNibble((v >> 12) & 0xF);
        s[4] = _hexNibble((v >> 8) & 0xF);
        s[5] = _hexNibble((v >> 4) & 0xF);
        s[6] = _hexNibble(v & 0xF);
        return string(s);
    }

    function _hexNibble(uint24 v) internal pure returns (bytes1) {
        return v < 10 ? bytes1(uint8(v + 48)) : bytes1(uint8(v + 87));
    }

    function _rareLayerId(uint8 rarityTypeId) internal pure returns (uint8) {
        if (rarityTypeId == RARITY_TYPE_ODD_EYES) return LAYER_RARE_ODD_EYES;
        if (rarityTypeId == RARITY_TYPE_RED_NOSE) return LAYER_RARE_RED_NOSE;
        if (rarityTypeId == RARITY_TYPE_BLUE_NOSE) return LAYER_RARE_BLUE_NOSE;
        if (rarityTypeId == RARITY_TYPE_GLASSES) return LAYER_RARE_GLASSES;
        if (rarityTypeId == RARITY_TYPE_SUNGLASSES) return LAYER_RARE_SUNGLASSES;
        return 255;
    }

    function _patternName(uint8 id) internal pure returns (string memory) {
        if (id == 0) return "solid";
        if (id == 1) return "socks";
        if (id == 2) return "pointed";
        if (id == 3) return "patched";
        if (id == 4) return "hachiware";
        if (id == 5) return "tuxedo";
        if (id == 6) return "masked";
        if (id == 7) return "classic_tabby";
        if (id == 8) return "mackerel_tabby";
        if (id == 9) return "tortoiseshell";
        if (id == 10) return "superrare";
        return "unknown";
    }

    function _paletteName(uint8 id) internal pure returns (string memory) {
        if (id == 0) return "black_white";
        if (id == 1) return "cyberpunk";
        if (id == 2) return "earth_tone";
        if (id == 3) return "gray_soft";
        if (id == 4) return "orange_warm";
        if (id == 5) return "orange_white";
        if (id == 6) return "psychedelic";
        if (id == 7) return "space_nebula";
        if (id == 8) return "tricolor_soft";
        if (id == 9) return "tropical_fever";
        if (id == 10) return "zombie";
        if (id == 11) return "ivory_brown";
        if (id == 12) return "black_solid";
        if (id == 13) return "superrare";
        return "unknown";
    }

    function _collarTypeName(uint8 id) internal pure returns (string memory) {
        if (id == COLLAR_NONE) return "none";
        if (id == COLLAR_CHECKERED) return "checkered_collar";
        if (id == COLLAR_CLASSIC_RED) return "classic_red_collar";
        return "none";
    }

    function _rarityTierName(uint8 id) internal pure returns (string memory) {
        if (id == RARITY_COMMON) return "common";
        if (id == RARITY_RARE) return "rare";
        if (id == RARITY_SUPERRARE) return "superrare";
        return "common";
    }

    function _rarityTypeName(uint8 id) internal pure returns (string memory) {
        if (id == RARITY_TYPE_NONE) return "none";
        if (id == RARITY_TYPE_ODD_EYES) return "odd_eyes";
        if (id == RARITY_TYPE_RED_NOSE) return "red_nose";
        if (id == RARITY_TYPE_BLUE_NOSE) return "blue_nose";
        if (id == RARITY_TYPE_GLASSES) return "glasses";
        if (id == RARITY_TYPE_SUNGLASSES) return "sunglasses";
        if (id == RARITY_TYPE_CORELOGO) return "corelogo";
        if (id == RARITY_TYPE_PINGLOGO) return "pinglogo";
        return "none";
    }
}
