import zipfile
import io
import struct
from pathlib import Path

BASE_DIR = Path("data/raw/corrosion_segmentation/extracted/Labeled images/Labeled images")


def inspect_labels():
    print(f"Base Directory: {BASE_DIR.resolve()}")
    
    # 1. Original images
    orig_dir = BASE_DIR / "Original images"
    orig_files = list(orig_dir.glob("*.tif"))
    print(f"Original images count (.tif): {len(orig_files)}")

    # 2. Label visualizations
    vis_dir = BASE_DIR / "Label visualization"
    vis_files = list(vis_dir.glob("*.tif"))
    print(f"Label visualization count (.tif): {len(vis_files)}")

    # 3. Corrosion label zips
    corr_dir = BASE_DIR / "Labels/Corrosion"
    corr_zips = list(corr_dir.glob("*.tif.zip"))
    print(f"Corrosion label zips count: {len(corr_zips)}")

    # 4. Background label zips
    bg_dir = BASE_DIR / "Labels/Background"
    bg_zips = list(bg_dir.glob("*.tif.zip"))
    print(f"Background label zips count: {len(bg_zips)}")

    # Inspect the internal structure of a sample corrosion zip
    sample_corr_zip = corr_zips[0]
    print(f"\nInspecting sample label zip: {sample_corr_zip.name}")
    with zipfile.ZipFile(sample_corr_zip, "r") as z:
        print("  Archive member names:", z.namelist())
        for member_name in z.namelist():
            raw_bytes = z.read(member_name)
            print(f"  Member '{member_name}' raw byte size: {len(raw_bytes)} bytes")
            # Check TIFF header (II\x2a\x00 for little endian or MM\x00\x2a for big endian)
            if raw_bytes[:2] in (b'II', b'MM'):
                endian = '<' if raw_bytes[:2] == b'II' else '>'
                magic = struct.unpack(f"{endian}H", raw_bytes[2:4])[0]
                ifd_offset = struct.unpack(f"{endian}I", raw_bytes[4:8])[0]
                print(f"  TIFF Header: Endian={raw_bytes[:2]}, Magic={magic}, First IFD Offset={ifd_offset}")
                
                # Parse IFD entries
                num_entries = struct.unpack(f"{endian}H", raw_bytes[ifd_offset:ifd_offset+2])[0]
                print(f"  IFD entries count: {num_entries}")
                tags = {}
                for idx in range(num_entries):
                    entry_off = ifd_offset + 2 + idx * 12
                    tag, tag_type, count, val_or_offset = struct.unpack(f"{endian}HHI I", raw_bytes[entry_off:entry_off+12])
                    tags[tag] = (tag_type, count, val_or_offset)
                
                # Tag 256 = ImageWidth, Tag 257 = ImageLength (Height), Tag 258 = BitsPerSample
                w = tags.get(256, (0, 0, 0))[2]
                h = tags.get(257, (0, 0, 0))[2]
                print(f"  Parsed TIFF dimensions: Width={w}, Height={h}")

    # Inspect sample original image TIFF
    sample_orig = orig_files[0]
    print(f"\nInspecting sample original image: {sample_orig.name}")
    with open(sample_orig, "rb") as f:
        raw_orig = f.read()
        print(f"  Raw file size: {len(raw_orig)} bytes ({len(raw_orig)/1024/1024:.2f} MB)")
        if raw_orig[:2] in (b'II', b'MM'):
            endian = '<' if raw_orig[:2] == b'II' else '>'
            ifd_offset = struct.unpack(f"{endian}I", raw_orig[4:8])[0]
            num_entries = struct.unpack(f"{endian}H", raw_orig[ifd_offset:ifd_offset+2])[0]
            tags = {}
            for idx in range(num_entries):
                entry_off = ifd_offset + 2 + idx * 12
                tag, tag_type, count, val_or_offset = struct.unpack(f"{endian}HHI I", raw_bytes[entry_off:entry_off+12])
                tags[tag] = (tag_type, count, val_or_offset)
            w = tags.get(256, (0, 0, 0))[2]
            h = tags.get(257, (0, 0, 0))[2]
            print(f"  Parsed Original TIFF dimensions: Width={w}, Height={h}")


if __name__ == "__main__":
    inspect_labels()
