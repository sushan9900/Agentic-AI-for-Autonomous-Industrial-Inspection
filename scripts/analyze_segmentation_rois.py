import zipfile
import struct
from pathlib import Path

BASE_DIR = Path("data/raw/corrosion_segmentation/extracted/Labeled images/Labeled images")


def parse_imagej_roi(roi_bytes: bytes):
    """Parses ImageJ 146-byte .roi binary file."""
    if len(roi_bytes) < 64:
        return None
    if roi_bytes[:4] != b'Iout':
        return None
    
    version = struct.unpack(">H", roi_bytes[4:6])[0]
    roi_type = struct.unpack(">H", roi_bytes[6:8])[0]  # 0=polygon, 1=rect, etc.
    top, left, bottom, right = struct.unpack(">hhhh", roi_bytes[8:16])
    width = right - left
    height = bottom - top
    return {
        "version": version,
        "type": roi_type,
        "top": top,
        "left": left,
        "bottom": bottom,
        "right": right,
        "width": width,
        "height": height
    }


def parse_tiff_dims(tiff_path: Path):
    with open(tiff_path, "rb") as f:
        data = f.read(1024)
        if data[:2] not in (b'II', b'MM'):
            return None, None
        endian = '<' if data[:2] == b'II' else '>'
        ifd_off = struct.unpack(f"{endian}I", data[4:8])[0]
        f.seek(ifd_off)
        num_entries = struct.unpack(f"{endian}H", f.read(2))[0]
        w, h = 0, 0
        for _ in range(num_entries):
            entry = f.read(12)
            if len(entry) < 12:
                break
            tag, tag_type, count, val = struct.unpack(f"{endian}HHI I", entry)
            if tag == 256:
                w = val
            elif tag == 257:
                h = val
        return w, h


def analyze_all():
    print("=== Analyzing Corrosion Segmentation Dataset (10.17632/kcyn4nhv2c.1) ===")
    
    orig_dir = BASE_DIR / "Original images"
    vis_dir = BASE_DIR / "Label visualization"
    corr_dir = BASE_DIR / "Labels/Corrosion"
    bg_dir = BASE_DIR / "Labels/Background"

    orig_files = sorted(orig_dir.glob("*.tif"))
    vis_files = sorted(vis_dir.glob("*.tif"))
    corr_zips = sorted(corr_dir.glob("*.tif.zip"))
    bg_zips = sorted(bg_dir.glob("*.tif.zip"))

    print(f"Original images (.tif): {len(orig_files)}")
    print(f"Visualization images (.tif): {len(vis_files)}")
    print(f"Corrosion label archives (.tif.zip): {len(corr_zips)}")
    print(f"Background label archives (.tif.zip): {len(bg_zips)}")

    # Image dimensions
    dims = []
    for f in orig_files:
        w, h = parse_tiff_dims(f)
        dims.append((w, h))

    widths = [w for w, h in dims if w > 0]
    heights = [h for w, h in dims if h > 0]
    print(f"\nImage Resolutions ({len(dims)} parsed):")
    print(f"  Widths: min={min(widths)}, max={max(widths)}, median={sorted(widths)[len(widths)//2]}")
    print(f"  Heights: min={min(heights)}, max={max(heights)}, median={sorted(heights)[len(heights)//2]}")

    # ROI analysis
    total_corr_rois = 0
    total_bg_rois = 0
    roi_sizes = []

    for cz in corr_zips:
        with zipfile.ZipFile(cz, "r") as z:
            names = z.namelist()
            total_corr_rois += len(names)
            for n in names:
                roi_info = parse_imagej_roi(z.read(n))
                if roi_info:
                    roi_sizes.append((roi_info["width"], roi_info["height"]))

    for bz in bg_zips:
        with zipfile.ZipFile(bz, "r") as z:
            names = z.namelist()
            total_bg_rois += len(names)

    print(f"\nAnnotation Analysis:")
    print(f"  Total Corrosion ROI patches: {total_corr_rois}")
    print(f"  Total Background ROI patches: {total_bg_rois}")
    print(f"  Total Sparse ROIs across dataset: {total_corr_rois + total_bg_rois}")
    print(f"  Sample ROI Dimensions (w, h): {set(roi_sizes)}")
    print(f"  Annotation Type: Sparse Patch-Level Coordinate ROIs (ImageJ .roi 5x5 px windows)")


if __name__ == "__main__":
    analyze_all()
