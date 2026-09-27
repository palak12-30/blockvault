/**
 * Converts a File object to a base64 string (no data-URL prefix),
 * matching the format the backend's upload_handler.py expects for
 * file_base64.
 */
export async function fileToBase64(file) {
  const buffer = await file.arrayBuffer();
  const bytes = new Uint8Array(buffer);
  let binary = "";
  for (let i = 0; i < bytes.length; i++) {
    binary += String.fromCharCode(bytes[i]);
  }
  return btoa(binary);
}
