import tempfile
from pathlib import Path
import unittest
import numpy as np
from inference_demo import sequences, mapping, Predictor, export_demo

class EquivalenceTests(unittest.TestCase):
    def test_region_context_and_overlaps(self):
        data = np.random.default_rng(9).normal(size=(200,4)).astype(np.float32)
        regions = [(0,20),(15,50),(100,200)]
        np.testing.assert_array_equal(sequences(data,regions,False),sequences(data,regions,True))
        expected = np.zeros((200,3),dtype=np.int64)
        expected[:15,0] = 1
        expected[15:50,1] = 1
        expected[100:,2] = 1
        for optimized in (False,True):
            np.testing.assert_array_equal(mapping(200,regions,[0,1,2],optimized),expected)

    def test_empty(self):
        x = sequences(np.zeros((10,4)),[],True)
        self.assertEqual(x.shape,(0,128,4))
        np.testing.assert_array_equal(mapping(10,[],[],True),np.zeros((10,3)))

    def test_real_backends_and_exclusive_loading(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)/'toy.onnx'
            export_demo(path)
            onnx = Predictor('onnx',path)
            torch = Predictor('torch',path)
            self.assertIsNone(onnx.model)
            self.assertIsNone(torch.session)
            x = np.random.default_rng(3).normal(size=(23,128,4)).astype(np.float32)
            left,right = onnx.predict(x),torch.predict(x)
            np.testing.assert_allclose(left,right,rtol=1e-5,atol=1e-6)
            np.testing.assert_array_equal(left.argmax(1),right.argmax(1))

if __name__ == '__main__':
    unittest.main()
