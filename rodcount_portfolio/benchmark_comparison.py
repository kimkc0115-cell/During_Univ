"""Fresh-process synthetic CPU comparison."""
import argparse
import hashlib
import json
from pathlib import Path
import statistics
import subprocess
import sys
import tempfile
import time

CASES = {
    'baseline_onnx_dual': ('onnx',False,True,0),
    'optimized_onnx': ('onnx',True,False,0),
    'baseline_torch_w4': ('torch',False,False,4),
    'optimized_torch': ('torch',True,False,0),
}

def worker(args):
    start = time.perf_counter()
    from inference_demo import Predictor, synthetic_data, sequences, mapping
    backend, optimized, dual, workers = CASES[args.worker]
    predictor = Predictor(backend,args.model,dual_load=dual,workers=workers)
    startup = time.perf_counter()-start
    data, regions = synthetic_data(args.rows)
    start = time.perf_counter()
    x = sequences(data,regions,optimized)
    pre = time.perf_counter()-start
    start = time.perf_counter()
    logits = predictor.predict(x)
    infer = time.perf_counter()-start
    start = time.perf_counter()
    result = mapping(len(data),regions,logits.argmax(axis=1),optimized)
    mapping_s = time.perf_counter()-start
    print(json.dumps(dict(startup_ms=startup*1000,preprocessing_ms=pre*1000,
        inference_pipeline_ms=infer*1000,mapping_ms=mapping_s*1000,
        calculation_ms=(pre+infer+mapping_s)*1000,
        result_sha256=hashlib.sha256(result.tobytes()).hexdigest())))

def measure(args,case,model):
    import psutil
    with tempfile.TemporaryFile(mode='w+',encoding='utf-8') as out, tempfile.TemporaryFile(mode='w+',encoding='utf-8') as err:
        start = time.perf_counter()
        child = subprocess.Popen([sys.executable,str(Path(__file__).resolve()),
            '--worker',case,'--model',str(model),'--rows',str(args.rows)],stdout=out,stderr=err)
        proc = psutil.Process(child.pid)
        peak = 0
        while child.poll() is None:
            try:
                processes = [proc]+proc.children(recursive=True)
            except psutil.Error:
                processes = [proc]
            rss = 0
            for process in processes:
                try:
                    rss += process.memory_info().rss
                except psutil.Error:
                    pass
            peak = max(peak,rss)
            time.sleep(.01)
        elapsed = time.perf_counter()-start
        out.seek(0)
        err.seek(0)
        if child.returncode:
            raise RuntimeError(err.read())
        result = json.load(out)
        result.update(case=case,peak_rss_mb=peak/1024**2,total_ms=elapsed*1000)
        return result

def main(args):
    from inference_demo import export_demo
    results = []
    with tempfile.TemporaryDirectory() as directory:
        model = Path(directory)/'synthetic.onnx'
        export_demo(model)
        for run in range(args.repeat):
            order = list(CASES) if run%2 == 0 else list(reversed(CASES))
            for case in order:
                item = measure(args,case,model)
                item['run'] = run+1
                results.append(item)
                print(f"{run+1}/{args.repeat} {case}: {item['calculation_ms']:.2f} ms, {item['peak_rss_mb']:.1f} MB",flush=True)
    equal = len({r['result_sha256'] for r in results}) == 1
    medians = {case:{key:statistics.median(r[key] for r in results if r['case']==case)
               for key in results[0] if key.endswith(('_ms','_mb'))} for case in CASES}
    reductions = {}
    for before,after in [('baseline_onnx_dual','optimized_onnx'),('baseline_torch_w4','optimized_torch')]:
        reductions[after] = {key:(1-medians[after][key]/medians[before][key])*100
                             for key in ('calculation_ms','peak_rss_mb')}
        print(f"{after}: calculation reduction {reductions[after]['calculation_ms']:.1f}%, RSS reduction {reductions[after]['peak_rss_mb']:.1f}%")
    import platform
    from importlib.metadata import version
    report = dict(dataset='synthetic seed=42; not production measurements',rows=args.rows,
        python=platform.python_version(),platform=platform.system(),device='CPU',
        versions={p:version(p) for p in ('numpy','torch','onnx','onnxruntime','psutil')},
        output_equal=equal,medians=medians,reductions_percent=reductions,samples=results)
    Path(args.output).write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(f'All output hashes equal: {equal}. Report: {args.output}')
    if not equal:
        raise RuntimeError('Output equivalence failed')

def cli():
    parser = argparse.ArgumentParser()
    parser.add_argument('--worker',choices=CASES)
    parser.add_argument('--model')
    parser.add_argument('--rows',type=int,default=300_000)
    parser.add_argument('--repeat',type=int,default=3)
    parser.add_argument('--output',default='benchmark_results.json')
    args = parser.parse_args()
    if args.rows<1000 or args.repeat<1:
        parser.error('rows >= 1000 and repeat >= 1 required')
    worker(args) if args.worker else main(args)

if __name__ == '__main__':
    cli()
