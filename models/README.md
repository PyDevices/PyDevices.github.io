# Models

Model files that OmniPython's browser pages fetch when an app first needs
them. GitHub Pages serves this site with `Access-Control-Allow-Origin: *`,
so a page on another address can fetch them.

| File | Used by | What it is | License |
|---|---|---|---|
| `yolo11n_coco_320.onnx` | Object detection in the all-apps page | YOLO11n, the 80 COCO classes, as ONNX at a 320 x 320 input (opset 17), 10,615,288 bytes, SHA-256 `fec7ab1ea72e967ac7f4a2b5cc74f6f154d6c1ff00ca597c0c9eabd06a3000ad` | AGPL-3.0 |

`yolo11n_coco_320.onnx` is Ultralytics' [YOLO11n](https://github.com/ultralytics/ultralytics)
weights, exported unchanged to ONNX by
[`scripts/export_yolo11n_onnx.py`](https://github.com/PyDevices/omnipython-builds/blob/main/scripts/export_yolo11n_onnx.py)
with Ultralytics 8.4.219. Ultralytics licenses the weights under
[AGPL-3.0](https://github.com/ultralytics/ultralytics/blob/main/LICENSE), not
this site's MIT licence. The page checks the SHA-256 above, so a new export
here needs the page's note changed with it.
