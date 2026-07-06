import os, glob
import csv
import cv2, math
import numpy as np
import itertools
from pathlib import Path

import pandas as pd

# ----------------------------
# GLOBAL STATE
# ----------------------------
pts1, pts2 = [], []
img1_disp, img2_disp = None, None
w1 = 0
scale1 = 1.0
scale2 = 1.0
batch_pts1 = []
batch_pts2 = []
BATCH_SIZE = 8
waiting_for_right = False
last_left_pt = None
current_F = None   # updated after each refinement
BATCH_SIZE = 8



def reprojection_error(H, p1, p2):
    p1_h = np.hstack([p1, np.ones((len(p1), 1))])
    proj = (H @ p1_h.T).T
    proj = proj[:, :2] / proj[:, 2:3]
    return np.linalg.norm(proj - p2, axis=1)


def mouse_callback(event, x, y, flags, param):
    global pts1, pts2, w1, scale1, scale2
    global waiting_for_right, last_left_pt, current_F

    if event != cv2.EVENT_LBUTTONDOWN:
        return

    # ----------------------------
    # BOOTSTRAP MODE (no F yet)
    # ----------------------------
    if current_F is None:
        if x < w1:
            pts1.append([x / scale1, y / scale1])
            print("L:", pts1[-1])
        else:
            pts2.append([(x - w1) / scale2, y / scale2])
            print("R:", pts2[-1])

        if len(pts1) != len(pts2):
            print("⚠ waiting for pair...")
        return

    # ----------------------------
    # GUIDED MODE (F exists)
    # ----------------------------
    # LEFT click → pick source point
    if x < w1 and not waiting_for_right:
        px, py = x / scale1, y / scale1
        last_left_pt = np.array([px, py], dtype=np.float32)
        waiting_for_right = True
        print("LEFT selected:", last_left_pt)
        return

    # RIGHT click → pick along epipolar line
    if x >= w1 and waiting_for_right:
        px, py = (x - w1) / scale2, y / scale2

        # optional: reject if far from epipolar line
        if current_F is not None:
            err = epipolar_error(
                current_F,
                np.array([last_left_pt]),
                np.array([[px, py]])
            )[0]
            print(f"epipolar error: {err:.2f}px")
            if err > 3.0:
                print("❌ far from epipolar line → try again")
                return

        pts1.append(last_left_pt.tolist())
        pts2.append([px, py])

        print("RIGHT selected:", [px, py])

        waiting_for_right = False
        last_left_pt = None
        return

    print("⚠ invalid click order")

def run_click_tool(img1, img2, max_size=800):

    global pts1, pts2, img1_disp, img2_disp, w1, scale1, scale2
    global waiting_for_right, last_left_pt, current_F

    # ----------------------------
    # RESET STATE
    # ----------------------------
    pts1, pts2 = [], []
    waiting_for_right = False
    last_left_pt = None
    current_F = None

    # ----------------------------
    # PREPARE DISPLAY
    # ----------------------------
    h1, w1_orig = img1.shape[:2]
    h2, w2_orig = img2.shape[:2]

    scale1 = 1 #min(max_size / w1_orig, max_size / h1, 1.0)
    scale2 = 1 #min(max_size / w2_orig, max_size / h2, 1.0)

    img1_disp = cv2.resize(img1, (int(w1_orig * scale1), int(h1 * scale1)))
    img2_disp = cv2.resize(img2, (int(w2_orig * scale2), int(h2 * scale2)))

    h1s, w1s = img1_disp.shape[:2]
    w1 = w1s  # boundary between images

    # ----------------------------
    # WINDOW SETUP
    # ----------------------------
    cv2.namedWindow("ANNOTATION", cv2.WINDOW_NORMAL)
    cv2.setMouseCallback("ANNOTATION", mouse_callback)

    print("Controls: click points | 'c' refine | 'f' finalize | 'q' quit")

    # ----------------------------
    # MAIN LOOP
    # ----------------------------
    while True:

        vis = np.hstack([img1_disp.copy(), img2_disp.copy()])

        # ----------------------------
        # DRAW EXISTING POINTS
        # ----------------------------
        for p in pts1:
            x = int(p[0] * scale1)
            y = int(p[1] * scale1)
            cv2.circle(vis, (x, y), 5, (0, 255, 0), -1)

        for p in pts2:
            x = int(w1 + p[0] * scale2)
            y = int(p[1] * scale2)
            cv2.circle(vis, (x, y), 5, (0, 0, 255), -1)


        # ----------------------------
        # UI HINT
        # ----------------------------

        cv2.putText(vis, "Collect >=8 pairs, press 'c'",
                        (10, 25), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (200, 200, 200), 2)


        cv2.imshow("ANNOTATION", vis)

        k = cv2.waitKey(10) & 0xFF

        # ----------------------------
        # REFINE (COMPUTE F + REMOVE OUTLIERS)
        # ----------------------------
        if k == ord('c'):

            if len(pts1) != len(pts2):
                print("⚠ incomplete pairs")
                continue

            if len(pts1) < BATCH_SIZE:
                print(f"⚠ need at least {BATCH_SIZE} pairs")
                continue

            print("Correspondences saved")
            break

        # ----------------------------
        # EXIT
        # ----------------------------
        if k == ord('q'):
            cv2.destroyAllWindows()
            return None, None

    cv2.destroyAllWindows()

    return np.array(pts1), np.array(pts2)


def closest_rectangle(x):

    m = int(math.isqrt(x))  # integer sqrt
    while x % m != 0:
        m -= 1
    n = x // m
    return m, n


def compute_homography(pts1, pts2, im_size, num_tiles = 4, image_mask = None):

    if pts1 is None or pts2 is None:
        return [], []

    # image after mask
    if image_mask is None:
        im_start_x, im_end_x, im_start_y, im_end_y = [0, im_size[1], 0, im_size[0]]
    else:
        im_start_x, im_end_x, im_start_y, im_end_y = image_mask

    # bbox for tiles
    grid = closest_rectangle(num_tiles)
    step_size_y, step_size_x = [int((im_end_y - im_start_y)/grid[1]), int((im_end_x - im_start_x)/grid[0])]

    grid_y = list(range(im_start_y, im_end_y+1, step_size_y))
    grid_x = list(range(im_start_x, im_end_x+1, step_size_x))

    # iterate over all tiles to compute H
    H_tiles, pts_tiles = [], []
    for i, x in enumerate(grid_x[:-1]):
        for j,y in enumerate(grid_y[:-1]):

            # points of image 1 per tiles
            # find points that are x < x_coord < x+1 and y < y_coord < y+1
            mask = (
                    (pts1[:, 0] < grid_x[i + 1]) & (pts1[:, 0] > x) &
                    (pts1[:, 1] < grid_y[j + 1]) & (pts1[:, 1] > y)
            )

            tile_pts1 = pts1[mask]
            tile_pts1[:, 0] -= im_start_x
            tile_pts1[:, 1] -= im_start_y

            tile_pts2 = pts2[mask]
            tile_pts2[:, 0] -= im_start_x
            tile_pts2[:, 1] -= im_start_y

            pts_tiles.append([tile_pts1, tile_pts2])

            try:
                H, inlier = cv2.findHomography(tile_pts1, tile_pts2, cv2.RANSAC, 10.0)
                H_tiles.append([(x, y), H])

            except cv2.error:
                print(f'Warning: not enough points in tile ({x},{y}). Empty homography')
                inlier, H = [], []
                H_tiles.append([(x, y), []])

            if H is None:
                break

            if len(H) > 3:
                pts1_h = np.hstack([tile_pts1, np.ones((len(tile_pts1), 1))])
                proj = (H @ pts1_h.T).T
                proj = proj[:, :2] / proj[:, 2:3]

                err = np.linalg.norm(proj - tile_pts2, axis=1)

                print(f"\n HOMOGRAPHY QUALITY Tiles ({x},{y})")
                print(f"mean error  : {err.mean():.2f}px")
                print(f"median error: {np.median(err):.2f}px")
                print(f"max error   : {err.max():.2f}px")
                print(f"inliers     : {np.sum(inlier)}/{len(inlier)}")

    # compute global H
    H_global, inlier_global = cv2.findHomography(pts1, pts2, cv2.RANSAC, 10.0)

    pts1_h = np.hstack([pts1, np.ones((len(pts1), 1))])
    proj = (H_global @ pts1_h.T).T
    proj = proj[:, :2] / proj[:, 2:3]

    err = np.linalg.norm(proj - pts2, axis=1)

    print("\n📊 HOMOGRAPHY QUALITY GLOBAL")
    print(f"mean error  : {err.mean():.2f}px")
    print(f"median error: {np.median(err):.2f}px")
    print(f"max error   : {err.max():.2f}px")
    print(f"inliers     : {np.sum(inlier_global)}/{len(inlier_global)}")


    return H_tiles, pts_tiles, H_global, [pts1, pts2]


# ----------------------------
# PER PAIR PROCESSING
# ----------------------------
def compute_homography_for_pair(img1_path, img2_path):

    global pts1, pts2

    pts1, pts2 = [], []

    img1 = cv2.imread(img1_path)
    img2 = cv2.imread(img2_path)

    im_size = img1.shape[0:2]

    pts1_out, pts2_out = run_click_tool(img1, img2, max_size=1400)

    if pts1_out is None or len(pts1_out) < 4:
        return None, None, None, None

    return compute_homography(pts1_out, pts2_out, im_size, num_tiles= 2, image_mask=[1280, 2560, 540, 1620])



def epipolar_error(F, p1, p2):
    p1_h = np.hstack([p1, np.ones((len(p1), 1))])
    p2_h = np.hstack([p2, np.ones((len(p2), 1))])

    # lines in image 2
    l2 = (F @ p1_h.T).T

    # distance point to line
    num = np.abs(np.sum(l2 * p2_h, axis=1))
    den = np.sqrt(l2[:,0]**2 + l2[:,1]**2)

    return num / den


def main(image_dir):

    gt_dir = image_dir + "/ground_truth"
    os.makedirs(gt_dir, exist_ok=True)

    csv_tiles = gt_dir + "/homographies_tiles.csv"
    csv_global = gt_dir + "/homographies_global.csv"

    img_paths = glob.glob(image_dir + '/*.png')
    img_names = [Path(path).name for path in img_paths]

    if not img_paths:
        print("No images found.")
        return

    all_pairs = list(itertools.combinations(img_names, 2))

    print(f"Found {len(img_paths)} images, {len(all_pairs)} pairs.")

    fieldnames = [
        'pair_id',
        'upper_corners_tiles',
        'img1',
        'img2',
        'homography_matrix',
        'correspondences'
    ]

    # -------------------------------------------------
    # LOAD EXISTING GT
    # -------------------------------------------------
    existing_pairs = set()

    if os.path.exists(csv_global):

        try:

            existing_df = pd.read_csv(csv_global)

            for _, row in existing_df.iterrows():

                pair = tuple(sorted([row["img1"], row["img2"]]))
                existing_pairs.add(pair)

            print(f"Loaded {len(existing_pairs)} existing GT pairs")

        except Exception as e:

            print("Could not read existing CSV")
            print(e)

    # -------------------------------------------------
    # FILTER NEW PAIRS
    # -------------------------------------------------
    pairs_to_process = []

    for pair in all_pairs:

        normalized = tuple(sorted(pair))

        if normalized in existing_pairs:

            print(f"Skipping existing pair: {pair}")
            continue

        pairs_to_process.append(pair)

    print(f"\nNeed annotation for {len(pairs_to_process)} new pairs")

    # -------------------------------------------------
    # CREATE CSVs IF THEY DON'T EXIST
    # -------------------------------------------------
    if not os.path.exists(csv_tiles):

        with open(csv_tiles, 'w', newline='') as f:

            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()

    if not os.path.exists(csv_global):

        with open(csv_global, 'w', newline='') as f:

            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()

    # -------------------------------------------------
    # PROCESS PAIRS
    # -------------------------------------------------
    for i, (img1_path, img2_path) in enumerate(pairs_to_process):

        pair_id = f"{i+1:03d}_{img1_path}-{img2_path}"

        print("\n====================================")
        print(f"Processing pair {i+1}/{len(pairs_to_process)}")
        print(pair_id)
        print("====================================")

        try:

            H_tiles, corrs_tiles, H_global, corrs_global = \
                compute_homography_for_pair(
                    str(image_dir + '/' + img1_path),
                    str(image_dir + '/' + img2_path)
                )

            if H_tiles is None and H_global is None:

                print("Skipped.")
                continue

            # -----------------------------------------
            # BUILD ENTRIES
            # -----------------------------------------
            entry_tiles = {
                "pair_id": pair_id,
                "upper_corners_tiles": [
                    np.array(H_tiles[i][0]).tolist()
                    for i in range(len(H_tiles))
                ],
                "img1": img1_path,
                "img2": img2_path,
                "homography_matrix": [
                    H_tiles[i][1].tolist()
                    if len(H_tiles[i][1]) > 0 else []
                    for i in range(len(H_tiles))
                ],
                "correspondences": corrs_tiles
            }

            entry_global = {
                "pair_id": pair_id,
                "upper_corners_tiles": None,
                "img1": img1_path,
                "img2": img2_path,
                "homography_matrix": H_global.tolist(),
                "correspondences": corrs_global
            }

            # -----------------------------------------
            # AUTO-SAVE IMMEDIATELY
            # -----------------------------------------
            with open(csv_tiles, 'a', newline='') as f:

                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writerow(entry_tiles)

            with open(csv_global, 'a', newline='') as f:

                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writerow(entry_global)

            print("✅ Auto-saved pair")

        except Exception as e:

            print("❌ Error processing pair")
            print(e)

            continue

    print("\n🎉 Annotation session complete")


if __name__ == "__main__":
    main("/mnt/WaddenSea WaddenSeaTestData/TestImages/ROV-StE2/products/GLDS0118_110509821_min_35_fps_1/small_subset_illum_change")