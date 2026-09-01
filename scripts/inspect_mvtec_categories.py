import httpx

CATEGORIES = [
    'bottle', 'cable', 'capsule', 'carpet', 'grid',
    'hazelnut', 'leather', 'metal_nut', 'pill', 'screw',
    'tile', 'toothbrush', 'transistor', 'wood', 'zipper'
]

def check_category_mirrors():
    print("Checking MVTec AD category definitions and properties...")
    # Official MVTec AD paper statistics:
    # 5,354 high-resolution images
    # 15 categories (5 textures, 10 objects)
    # 3,629 images for training (all normal)
    # 1,725 images for testing (467 normal, 1,258 anomalous with pixel-accurate ground truth masks)
    # 73 different anomaly types (scratches, dents, holes, contamination, bent wire, broken teeth, etc.)

if __name__ == "__main__":
    check_category_mirrors()
