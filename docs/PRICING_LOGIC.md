# Model Pricing Logic

This document describes the pricing logic for different LLM providers supported by the MultiPromptSandbox.

## OpenAI

### Text Models (GPT-4o, GPT-4 Turbo, GPT-3.5 Turbo)
- **Input:** Per 1,000,000 tokens.
- **Output:** Per 1,000,000 tokens.
- **Batch API:** 50% discount on input and output prices (if supported).

### Image Input (Vision)
- **Mode:** Token-based (Tiles).
- **Calculation:**
  - **Low Detail:** Fixed **85 tokens**.
  - **High Detail:**
    1.  **Scale:** Image scaled to fit within 2048x2048.
    2.  **Scale:** Then scaled so shortest side is 768px.
    3.  **Tile:** Divided into 512x512 tiles.
    4.  **Formula:** `85 (base) + (num_tiles * 170)`.
- **Cost:** Calculated as part of the Input Token cost.

## Anthropic (Claude)

### Text Models (Claude 3.5 Sonnet, Claude 3 Opus, Claude 3 Haiku)
- **Input:** Per 1,000,000 tokens.
- **Output:** Per 1,000,000 tokens.

### Image Input
- **Mode:** Token-based (approximate).
- **Calculation:**
  - **Formula:** `(width * height) / 750` tokens (approximate).
  - **Max Tokens:** Images are resized if exceeding ~1.15 megapixels or 1568px on long edge.
  - **Typical:** ~1600 tokens for optimal size.
- **Cost:** Calculated as part of the Input Token cost.

## Google Vertex AI (Gemini)

### Text Models (Gemini 1.5 Pro, Gemini 1.5 Flash)
- **Input:** Per 1,000,000 tokens (Text).
- **Output:** Per 1,000,000 tokens.
- **Context Caching:** Discounted rates for cached input.

### Image Input
- **Mode:**
  - **Gemini 1.5 Pro:** Token-based (approx 258 tokens per image regardless of size, if < 3072x3072? *Need verification, often treated as fixed tokens or pixel-based tokens*).
  - **Gemini 1.5 Flash:** **Per Image** flat rate (e.g., $0.00002/image) OR Token-based depending on specific SKU/Pricing tier.
  - **Video:** Per second.

## Database Schema Implications (`ModelConfig.pricing_config`)

The `pricing_config` JSON field should support these structures:

**Generic Token-Based:**
```json
{
  "mode": "token_based",
  "input_price_per_1m": 2.50,
  "output_price_per_1m": 10.00,
  "image_input_mode": "token_converted", // Images are converted to tokens
  "image_token_calc": "openai_tiles" // or "anthropic_pixel_ratio", "fixed_tokens"
}
```

**Google Per-Image Input:**
```json
{
  "mode": "token_based", // Text is still token based
  "input_price_per_1m": 0.35,
  "output_price_per_1m": 1.05,
  "image_input_mode": "per_image",

## Configuration Examples

Here are example JSON payloads for the `pricing_config` field in `ModelConfig` to match the implemented logic.

### OpenAI (GPT-4o)
Uses precise tiling calculation for images.

```json
{
  "mode": "token_based",
  "input_price_per_1m": 5.00,
  "output_price_per_1m": 15.00,
  "image_price_mode": "per_tile",
  "image_token_calc": "openai_tiles",
  "discount_percent": 0
}
```

### Anthropic (Claude 3.5 Sonnet)
Uses pixel-ratio based token estimation.

```json
{
  "mode": "token_based",
  "input_price_per_1m": 3.00,
  "output_price_per_1m": 15.00,
  "image_price_mode": "per_token",
  "image_token_calc": "anthropic_pixel_ratio",
  "discount_percent": 0
}
```

### Google (Gemini 1.5 Flash)
Often uses a flat rate per image input.

```json
{
  "mode": "token_based",
  "input_price_per_1m": 0.35,
  "output_price_per_1m": 1.05,
  "image_price_mode": "per_image",
  "image_price_val": 0.00002,
  "discount_percent": 0
}
```
