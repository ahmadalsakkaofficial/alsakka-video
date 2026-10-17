import Vision; import AppKit
// prints: path minX topY width chinY  (normalized, top-left origin) — chin = lowest face-contour point
for p in CommandLine.arguments.dropFirst() {
  guard let img = NSImage(contentsOfFile: p), let cg = img.cgImage(forProposedRect: nil, context: nil, hints: nil) else { print(p, "none"); continue }
  let r = VNDetectFaceLandmarksRequest(); try? VNImageRequestHandler(cgImage: cg).perform([r])
  if let f = (r.results ?? []).max(by: { $0.boundingBox.width < $1.boundingBox.width }) {
    let b = f.boundingBox; var chin = 1 - b.minY
    if let fc = f.landmarks?.faceContour { chin = fc.normalizedPoints.map { 1 - (b.minY + $0.y * b.height) }.max() ?? chin }
    print(p, String(format: "%.4f %.4f %.4f %.4f", b.minX, 1 - b.maxY, b.width, chin))
  } else { print(p, "none") }
}
