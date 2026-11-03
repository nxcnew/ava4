// Finds faces in images with macOS Vision and prints JSON: {"<path>": [[x, top, w, h], ...]}, all as fractions of
// the image, measured from its top-left corner. make-manifest.sh stores them so index.html can keep faces in view.
//     swift scripts/faces.swift walls/a.png walls/b.png
import Foundation
import Vision

var out: [String: [[Double]]] = [:]
for path in CommandLine.arguments.dropFirst() {
    let req = VNDetectFaceRectanglesRequest()
    let handler = VNImageRequestHandler(url: URL(fileURLWithPath: path), options: [:])
    do { try handler.perform([req]) } catch { continue }
    let faces: [VNFaceObservation] = req.results ?? []
    out[path] = faces.filter { $0.confidence > 0.5 }.map { (f: VNFaceObservation) -> [Double] in
        let b = f.boundingBox  // normalised, origin bottom-left
        return [b.minX, 1 - b.maxY, b.width, b.height].map { (Double($0) * 10000).rounded() / 10000 }
    }
}
let data = try! JSONSerialization.data(withJSONObject: out, options: [.sortedKeys])
print(String(data: data, encoding: .utf8)!)
