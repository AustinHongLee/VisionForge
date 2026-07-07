export const isSafeExternalUrl = (url: string): boolean => {
  if (url.length === 0 || url.trim() !== url) {
    return false;
  }

  try {
    const parsedUrl = new URL(url);
    return parsedUrl.protocol === "http:" || parsedUrl.protocol === "https:";
  } catch {
    return false;
  }
};
