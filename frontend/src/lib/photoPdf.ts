/**
 * Photos of notebook pages, joined into one PDF in the browser.
 *
 * One document per set of pages, not one per photo, so a lecture written over
 * five pages becomes one set of concepts and quizzes. Each photo is shrunk
 * first: a phone photo is 3-5MB, and the AI reads handwriting just as well at
 * 2000 pixels on the long side.
 */

const LONG_EDGE = 2000;
const JPEG_QUALITY = 0.82;

interface PageImage {
  jpeg: Uint8Array;
  width: number;
  height: number;
}

function loadImage(file: File): Promise<HTMLImageElement> {
  return new Promise((resolve, reject) => {
    const url = URL.createObjectURL(file);
    const image = new Image();
    image.onload = () => {
      URL.revokeObjectURL(url);
      resolve(image);
    };
    image.onerror = () => {
      URL.revokeObjectURL(url);
      reject(new Error(`Could not open ${file.name}. Try taking the photo again.`));
    };
    image.src = url;
  });
}

/** The photo as a JPEG no larger than LONG_EDGE, upright (browsers apply the camera's rotation when drawing). */
async function shrink(file: File): Promise<PageImage> {
  const image = await loadImage(file);
  const scale = Math.min(1, LONG_EDGE / Math.max(image.naturalWidth, image.naturalHeight));
  const width = Math.max(1, Math.round(image.naturalWidth * scale));
  const height = Math.max(1, Math.round(image.naturalHeight * scale));
  const canvas = document.createElement("canvas");
  canvas.width = width;
  canvas.height = height;
  const context = canvas.getContext("2d");
  if (!context) throw new Error("This browser cannot prepare photos.");
  // White behind a transparent screenshot, not black.
  context.fillStyle = "#fff";
  context.fillRect(0, 0, width, height);
  context.drawImage(image, 0, 0, width, height);
  const blob = await new Promise<Blob | null>((resolve) => canvas.toBlob(resolve, "image/jpeg", JPEG_QUALITY));
  if (!blob) throw new Error("This browser cannot prepare photos.");
  return { jpeg: new Uint8Array(await blob.arrayBuffer()), width, height };
}

/** A PDF with one page per JPEG, each page the photo's own shape. */
export function buildPdf(pages: PageImage[]): Blob {
  const encoder = new TextEncoder();
  const chunks: Uint8Array[] = [];
  const offsets: number[] = [];
  let length = 0;
  const push = (part: string | Uint8Array) => {
    const bytes = typeof part === "string" ? encoder.encode(part) : part;
    chunks.push(bytes);
    length += bytes.length;
  };
  const object = (id: number, body: string | (string | Uint8Array)[]) => {
    offsets[id] = length;
    push(`${id} 0 obj\n`);
    for (const part of Array.isArray(body) ? body : [body]) push(part);
    push("\nendobj\n");
  };

  // Objects: 1 catalog, 2 page tree, then per page: page, image, contents.
  const pageIds = pages.map((_, index) => 3 + index * 3);
  push("%PDF-1.4\n%âãÏÓ\n");
  object(1, "<< /Type /Catalog /Pages 2 0 R >>");
  object(2, `<< /Type /Pages /Kids [${pageIds.map((id) => `${id} 0 R`).join(" ")}] /Count ${pages.length} >>`);
  pages.forEach((page, index) => {
    const [pageId, imageId, contentId] = [pageIds[index], pageIds[index] + 1, pageIds[index] + 2];
    // 72 points per inch at 150 dpi: about A4 for a 2000-pixel photo.
    const w = ((page.width * 72) / 150).toFixed(2);
    const h = ((page.height * 72) / 150).toFixed(2);
    object(
      pageId,
      `<< /Type /Page /Parent 2 0 R /MediaBox [0 0 ${w} ${h}] /Resources << /XObject << /Im${index} ${imageId} 0 R >> >> /Contents ${contentId} 0 R >>`,
    );
    object(imageId, [
      `<< /Type /XObject /Subtype /Image /Width ${page.width} /Height ${page.height} /ColorSpace /DeviceRGB /BitsPerComponent 8 /Filter /DCTDecode /Length ${page.jpeg.length} >>\nstream\n`,
      page.jpeg,
      "\nendstream",
    ]);
    const draw = `q ${w} 0 0 ${h} 0 0 cm /Im${index} Do Q`;
    object(contentId, `<< /Length ${draw.length} >>\nstream\n${draw}\nendstream`);
  });

  const count = 3 + pages.length * 3;
  const xref = length;
  push(`xref\n0 ${count}\n0000000000 65535 f \n`);
  for (let id = 1; id < count; id += 1) push(`${String(offsets[id]).padStart(10, "0")} 00000 n \n`);
  push(`trailer\n<< /Size ${count} /Root 1 0 R >>\nstartxref\n${xref}\n%%EOF\n`);
  return new Blob(chunks as BlobPart[], { type: "application/pdf" });
}

/** The pages, in order, as one PDF file named after the notes. */
export async function photosToPdf(photos: File[], title: string): Promise<File> {
  const pages: PageImage[] = [];
  for (const photo of photos) pages.push(await shrink(photo));
  const name = (title.trim() || "Photographed notes").replace(/[\\/:*?"<>|]+/g, " ").slice(0, 80);
  return new File([buildPdf(pages)], `${name}.pdf`, { type: "application/pdf" });
}
