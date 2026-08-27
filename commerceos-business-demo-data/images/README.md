# Product Image Assets

The demo catalog references free stock imagery primarily from Unsplash.

## Important licensing note

Unsplash's regular license permits broad free use, including commercial use, but additional rights can matter for recognizable people, trademarks/logos, and depicted copyrighted works. For the final production merchant catalog, use merchant-owned product photography or verify the rights for every image.

For Unsplash API usage, follow the API's hotlinking and attribution requirements. If the application uses the Unsplash API, do not simply download and rehost API images; use the returned image URLs according to the API guidelines.

## Files

`image_manifest.json` maps every `image_key` to its source page and image information.

## Recommended production approach

1. Merchant uploads product images to Supabase Storage.
2. Store the Storage object path in PostgreSQL.
3. Generate optimized variants.
4. Use Next.js Image for delivery.
5. Keep the original source/license metadata for demo/stock assets.

The current dataset intentionally uses fictional product names so the demo does not imply affiliation with real brands.
