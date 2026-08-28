/**
 * Real product photography, hotlinked from Unsplash's CDN (permissive licence,
 * hotlink-friendly — unlike Google Images thumbnails, which block referrers).
 * Resolved by the product's `image_key` first, then its catalogue category.
 * The UI always falls back to a generated tile if the image fails to load.
 */
const BY_IMAGE_KEY: Record<string, string> = {
  laptop_01: "photo-1517336714731-489689fd1ca8",
  phone_01: "photo-1511707171634-5f897ff02aa9",
  headphones_01: "photo-1505740420928-5e560c06d30e",
  keyboard_01: "photo-1587829741301-dc798b83add3",
  mouse_01: "photo-1527814050087-3793815479db",
  watch_01: "photo-1523275335684-37898b6baf30",
  hub_01: "photo-1625842268584-8f3296236761",
  stand_01: "photo-1527864550417-7fd91fc51a46",
  // accessories add-on set
  sleeve_01: "photo-1547949003-9792a18a2601",
  backpack_01: "photo-1553062407-98eeb64c6a62",
  charger_01: "photo-1583863788434-e58a36330cf0",
  powerbank_01: "photo-1609091839311-d5365f9ff1c5",
  ssd_01: "photo-1531492746076-161ca9bcad58",
  webcam_01: "photo-1590935217281-8f102120d683",
  dock_01: "photo-1625842268584-8f3296236761",
  coolingpad_01: "photo-1616763355603-9755a640a287",
  monitor_01: "photo-1527443154391-507e9dc6c5cc",
  cablekit_01: "photo-1558618666-fcd25c85cd64",
  mic_01: "photo-1590602847861-f357a9332bbc",
};

const BY_CATEGORY: Record<string, string> = {
  Laptops: "photo-1517336714731-489689fd1ca8",
  Smartphones: "photo-1511707171634-5f897ff02aa9",
  Audio: "photo-1505740420928-5e560c06d30e",
  Keyboards: "photo-1587829741301-dc798b83add3",
  Mice: "photo-1527814050087-3793815479db",
  Wearables: "photo-1523275335684-37898b6baf30",
  Accessories: "photo-1625948515291-69613efd103f",
  Storage: "photo-1531492746076-161ca9bcad58",
  Displays: "photo-1527443154391-507e9dc6c5cc",
  Bags: "photo-1553062407-98eeb64c6a62",
  Power: "photo-1583863788434-e58a36330cf0",
};

const DEFAULT_ID = "photo-1498049794561-7780e7231661"; // generic electronics

export function productImageUrl(
  category: string | null | undefined,
  imageKey?: string | null,
  width = 480,
): string {
  const id =
    (imageKey && BY_IMAGE_KEY[imageKey]) ||
    (category && BY_CATEGORY[category]) ||
    DEFAULT_ID;
  return `https://images.unsplash.com/${id}?auto=format&fit=crop&w=${width}&q=70`;
}
