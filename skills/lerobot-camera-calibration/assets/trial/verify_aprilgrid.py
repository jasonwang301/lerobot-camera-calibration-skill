"""Offline checks for this user's photographed board; never opens devices."""

import json
import sys
import unittest
from pathlib import Path

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "cyberwave-edge-so101"))
from utils.cw_handeye import board_from_spec


class AprilGridChecks(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.spec = json.loads((ROOT / "configs/user-aprilgrid.json").read_text())
        cls.board = board_from_spec(cls.spec)
        cls.photo = cv2.imread(str(ROOT / "assets/user-aprilgrid-reference.jpg"))
        cls.metrics = {}

    def test_reference_photo_and_corner_order(self):
        (objects, pixels), count = self.board.detect(cv2, self.photo)
        self.assertEqual(count, 88)
        self.assertEqual(objects.shape, (352, 3))
        # Independent, hand-checked anchors in the supplied photo: ID3 is the
        # top-left tag, ID90 the bottom-right, and each code points upward.
        detector = cv2.aruco.ArucoDetector(
            cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_APRILTAG_36h11),
            cv2.aruco.DetectorParameters(),
        )
        _corners, ids, _ = detector.detectMarkers(self.photo)
        for tag_id, expected in (
            (3, [[0, .049, 0], [0, 0, 0], [.049, 0, 0], [.049, .049, 0]]),
            (90, [[.427, .659, 0], [.427, .610, 0], [.476, .610, 0], [.476, .659, 0]]),
        ):
            index = ids.ravel().tolist().index(tag_id)
            np.testing.assert_allclose(objects[4 * index:4 * index + 4], expected, atol=1e-10)
        homography, mask = cv2.findHomography(objects[:, :2], pixels, cv2.RANSAC, 3)
        projected = cv2.perspectiveTransform(objects[:, :2].reshape(-1, 1, 2), homography)
        errors = np.linalg.norm(projected.reshape(-1, 2) - pixels, axis=1)
        self.assertLess(np.median(errors), 3)
        self.assertGreater(np.mean(mask), .75)
        self.metrics.update(
            reference_tags=count, reference_corners=len(objects),
            photo_homography_median_px=float(np.median(errors)),
            photo_homography_inlier_count=int(mask.sum()),
        )

    def test_partial_photo_and_unknown_tag(self):
        cropped = self.photo[360:1080, 300:900]
        (objects, _pixels), count = self.board.detect(cv2, cropped)
        self.assertGreaterEqual(count, 6)
        self.assertLess(count, 88)
        self.assertGreater(np.min(objects[:, 0]), 0)
        self.metrics["partial_photo_tags"] = count
        dictionary = cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_APRILTAG_36h11)
        foreign = cv2.aruco.generateImageMarker(dictionary, 100, 200)
        foreign = cv2.copyMakeBorder(foreign, 30, 30, 30, 30, cv2.BORDER_CONSTANT, value=255)
        self.assertIsNone(self.board.correspondences(cv2, foreign, minimum=1))

    def test_rendered_corner_order_all_rotations(self):
        for rotation in range(4):
            board = board_from_spec({**self.spec, "tag_rotation_ccw": rotation})
            # 196 px/49 mm gives exactly 48 px/12 mm gap (4000 px/m).
            image = cv2.copyMakeBorder(board.generate_image(196), 40, 40, 40, 40,
                                       cv2.BORDER_CONSTANT, value=255)
            (objects, pixels), count = board.detect(cv2, image)
            self.assertEqual(count, 88)
            # Raster tag borders lie half a pixel outside the outermost samples.
            expected = objects[:, :2] * 4000 + 39.5
            self.assertLess(float(np.max(np.linalg.norm(expected - pixels, axis=1))), 1)

    def test_invalid_specs_are_refused(self):
        for updates in (
            {"tag_size_m": None}, {"tag_gap_m": None}, {"tag_size_m": 0},
            {"tag_gap_m": float("nan")}, {"tag_rotation_ccw": 4},
            {"id_order": "unknown"}, {"type": "typo"},
        ):
            with self.assertRaises(ValueError):
                board_from_spec({**self.spec, **updates})
        self.assertEqual(board_from_spec(self.board.to_metadata()), self.board)
        np.testing.assert_allclose(self.board.extent_m, [.476, .659])


if __name__ == "__main__":
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(AprilGridChecks)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    payload = {
        "passed": result.wasSuccessful(), "tests_run": result.testsRun,
        "board": AprilGridChecks.spec, "metrics": AprilGridChecks.metrics,
        "synthetic_checks_are_not_camera_calibration": True,
        "actual_hardware_calibrated": False,
    }
    (ROOT / "artifacts/aprilgrid-verification.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n")
    raise SystemExit(0 if result.wasSuccessful() else 1)
