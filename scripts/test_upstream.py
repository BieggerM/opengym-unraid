import unittest
from upstream import amd64_digest, needs_rebuild


class UpdateDetection(unittest.TestCase):
    def setUp(self):
        self.labels = {"io.opengym.upstream.api": "api@old", "io.opengym.upstream.web": "web@old",
                       "org.opencontainers.image.revision": "commit-a"}

    def test_unchanged_images_and_packaging_skip_rebuild(self):
        self.assertFalse(needs_rebuild(self.labels, "api@old", "web@old", "commit-a"))

    def test_each_input_change_triggers_rebuild(self):
        for inputs in [("api@new", "web@old", "commit-a"),
                       ("api@old", "web@new", "commit-a"),
                       ("api@old", "web@old", "commit-b")]:
            with self.subTest(inputs=inputs):
                self.assertTrue(needs_rebuild(self.labels, *inputs))

    def test_first_publication_builds(self):
        self.assertTrue(needs_rebuild({}, "api@old", "web@old", "commit-a"))

    def test_selects_amd64_and_ignores_attestations(self):
        digest = "sha256:" + "a" * 64
        manifest = {"manifests": [
            {"digest": "sha256:" + "b" * 64, "platform": {"os": "linux", "architecture": "arm64"}},
            {"digest": digest, "platform": {"os": "linux", "architecture": "amd64"}},
            {"digest": "sha256:" + "c" * 64, "platform": {"os": "unknown", "architecture": "unknown"}},
        ]}
        self.assertEqual(amd64_digest(manifest), digest)

    def test_missing_amd64_and_invalid_digest_fail(self):
        with self.assertRaises(ValueError):
            amd64_digest({"manifests": []})
        with self.assertRaises(ValueError):
            amd64_digest({"digest": "not-a-digest"})


if __name__ == "__main__":
    unittest.main()
