"""Synthetic reconstruction, without production models or business rules."""
import numpy as np

def synthetic_data(rows=300_000):
    data = np.random.default_rng(42).normal(size=(rows, 4)).astype(np.float32)
    return data, [(s, s+600) for s in range(100, rows-600, 10000)]

def scale(x):
    return (x - np.array([.1,.2,.3,.4], dtype=np.float32)) / np.float32(2)

def sequences(data, regions, optimized):
    full = None if optimized else scale(data.copy())
    result = []
    for start, end in regions:
        values = scale(data[start:end].copy()) if optimized else full[start:end]
        indices = np.linspace(0, len(values)-1, 128).astype(int)
        result.append(values[indices])
    return np.asarray(result, dtype=np.float32).reshape(-1,128,4)

def mapping(rows, regions, classes, optimized):
    if optimized:
        result = np.zeros((rows,3), dtype=np.int64)
        for (start,end), label in zip(regions,classes):
            result[start:end] = 0
            result[start:end,label] = 1
        return result
    result = [[0,0,0] for _ in range(rows)]
    for (start,end), label in zip(regions,classes):
        for row in range(start,end):
            result[row] = [int(i == label) for i in range(3)]
    return np.asarray(result, dtype=np.int64)

def torch_model():
    import torch
    class ToyClassifier(torch.nn.Module):
        def forward(self,x):
            return x.mean(dim=1)[:,:3]
    return ToyClassifier().eval()

def export_demo(path):
    import onnx
    from onnx import helper, TensorProto
    graph = helper.make_graph([
        helper.make_node('ReduceMean',['input'],['mean'],axes=[1],keepdims=0),
        helper.make_node('Gather',['mean','indices'],['logits'],axis=1)],
        'synthetic_classifier',
        [helper.make_tensor_value_info('input',TensorProto.FLOAT,['batch',128,4])],
        [helper.make_tensor_value_info('logits',TensorProto.FLOAT,['batch',3])],
        [helper.make_tensor('indices',TensorProto.INT64,[3],[0,1,2])])
    model = helper.make_model(graph,opset_imports=[helper.make_opsetid('',13)])
    model.ir_version = 8
    onnx.checker.check_model(model)
    onnx.save(model,str(path))

#이하 핵심
class Predictor:
    def __init__(self,backend,model_path,dual_load=False,workers=0):
        if backend not in ('onnx','torch'):
            raise ValueError('backend must be onnx or torch') #Error message
        self.backend, self.workers = backend, workers
        self.model = self.session = None
        if dual_load or backend == 'torch':
            import torch
            torch.set_num_threads(1)
            self.model = torch_model()
        if dual_load or backend == 'onnx':
            import onnxruntime as ort
            options = ort.SessionOptions()
            options.intra_op_num_threads = 1
            options.inter_op_num_threads = 1
            self.session = ort.InferenceSession(str(model_path),options,providers=['CPUExecutionProvider'])

    def predict(self,x):
        if not len(x):
            return np.empty((0,3),dtype=np.float32)
        if self.backend == 'onnx':
            return np.concatenate([self.session.run(None,{'input':x[s:s+16]})[0]
                                   for s in range(0,len(x),16)])
        import torch
        from torch.utils.data import DataLoader, TensorDataset
        loader = DataLoader(TensorDataset(torch.from_numpy(x)),batch_size=16,
                            num_workers=self.workers,pin_memory=False)
        with torch.inference_mode():
            return np.concatenate([self.model(batch).numpy() for (batch,) in loader])
