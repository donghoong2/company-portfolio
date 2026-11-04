// PDF → 페이지별 PNG (macOS PDFKit). preview.sh가 컴파일해 scripts/.bin/pdf2png로 캐시한다.
// 사용법: pdf2png <in.pdf> <outdir> [scale=2]   출력: <outdir>/page.NNN.png, 표준출력에 페이지 수
import Foundation
import PDFKit
import AppKit
let a = CommandLine.arguments
guard a.count >= 3, let doc = PDFDocument(url: URL(fileURLWithPath: a[1])) else { fputs("usage: pdf2png <in.pdf> <outdir> [scale]\n", stderr); exit(2) }
let scale = a.count > 3 ? CGFloat(Double(a[3]) ?? 2) : 2
for i in 0..<doc.pageCount {
  guard let page = doc.page(at: i) else { continue }
  let box = page.bounds(for: .mediaBox)
  let w = Int(box.width * scale), h = Int(box.height * scale)
  guard let ctx = CGContext(data: nil, width: w, height: h, bitsPerComponent: 8, bytesPerRow: 0, space: CGColorSpaceCreateDeviceRGB(), bitmapInfo: CGImageAlphaInfo.premultipliedLast.rawValue) else { exit(1) }
  ctx.setFillColor(CGColor(red: 1, green: 1, blue: 1, alpha: 1)); ctx.fill(CGRect(x: 0, y: 0, width: w, height: h))
  ctx.scaleBy(x: scale, y: scale)
  page.draw(with: .mediaBox, to: ctx)
  guard let img = ctx.makeImage() else { exit(1) }
  let rep = NSBitmapImageRep(cgImage: img)
  let out = URL(fileURLWithPath: a[2]).appendingPathComponent(String(format: "page.%03d.png", i + 1))
  try! rep.representation(using: .png, properties: [:])!.write(to: out)
}
print(doc.pageCount)
