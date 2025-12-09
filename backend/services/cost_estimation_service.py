import logging
import math
import tiktoken
from typing import Optional, Dict, List, Any, Union
from sqlalchemy.orm import Session
import base64
import io
from PIL import Image as PILImage

from models.evaluation import ModelConfig, Evaluation, EvaluationResult
from models.labelling_job import LabellingJob
from models.image import Image
from models.project import Project

logger = logging.getLogger(__name__)

class CostEstimationService:
    """Service for estimating and calculating costs for LLM operations"""

    def __init__(self):
        self._tiktoken_cache = {}

    def _get_encoding(self, model_name: str):
        """Get tiktoken encoding for model"""
        try:
            return tiktoken.encoding_for_model(model_name)
        except KeyError:
            # Fallback for non-OpenAI or unknown models
            return tiktoken.get_encoding("cl100k_base")

    def count_tokens(self, text: str, provider: str, model_name: str) -> int:
        """
        Count tokens in text.
        For OpenAI, uses tiktoken.
        For others, uses heuristic (1 token ~= 4 chars).
        """
        if not text:
            return 0

        if provider == 'openai':
            try:
                encoding = self._get_encoding(model_name)
                return len(encoding.encode(text))
            except Exception:
                # Fallback to heuristic
                return len(text) // 4
        else:
            # Simple heuristic for Gemini/Claude/others
            # 1 token ~= 4 characters (English)
            return len(text) // 4

    def calculate_image_cost(self, image_data_b64: str, mime_type: str, pricing_config: Dict[str, Any]) -> float:
        """
        Calculate cost for a single image based on pricing config.

        pricing_config fields:
        - image_price_mode: 'per_image', 'per_token', 'per_tile'
        - image_price_val: float (cost per image/token) or dict (for tile params)
        """
        mode = pricing_config.get('image_price_mode', 'per_image')
        price_val = pricing_config.get('image_price_val', 0.0)

        if mode == 'per_image':
            return float(price_val)

        elif mode == 'per_token':
            # Need to estimate tokens first
            # Default heuristic: 1 image = 258 tokens (Claude approx) or custom
            tokens = 258
            # If price_val is cost per 1M tokens
            return (tokens / 1_000_000) * float(price_val)

        elif mode == 'per_tile':
            # OpenAI style: Low detail = 85 tokens. High detail = tiles * 170 + 85.
            # We need image dimensions to calculate tiles.
            try:
                # Decode image header to get size
                img_bytes = base64.b64decode(image_data_b64)
                with PILImage.open(io.BytesIO(img_bytes)) as img:
                    width, height = img.size

                # Default to High detail calculation logic from OpenAI
                # 1. Scale to fit within 2048x2048
                # 2. Scale shortest side to 768px
                # 3. Count 512px tiles

                # Simplified tile calc:
                # ceil(width/512) * ceil(height/512) * 170 + 85
                # Note: This is an approximation of OpenAI's complex logic
                h_tiles = math.ceil(width / 512)
                v_tiles = math.ceil(height / 512)
                total_tiles = h_tiles * v_tiles

                tokens = (total_tiles * 170) + 85

                # price_val assumed to be cost per 1M tokens (input price)
                return (tokens / 1_000_000) * float(price_val)

            except Exception as e:
                logger.warning(f"Failed to calculate image tiles: {e}")
                return 0.002 # Fallback cost

        return 0.0

    def estimate_request_cost(
        self,
        input_text: str,
        output_text_est: str,
        images: List[str],
        model_config: ModelConfig
    ) -> float:
        """
        Estimate cost for a single LLM request.
        """
        if not model_config.pricing_config:
            return 0.0

        pc = model_config.pricing_config
        input_price_1m = float(pc.get('input_price_per_1m', 0))
        output_price_1m = float(pc.get('output_price_per_1m', 0))

        # Input Text Cost
        input_tokens = self.count_tokens(input_text, model_config.provider, model_config.model_name)
        input_cost = (input_tokens / 1_000_000) * input_price_1m

        # Output Text Cost (Estimated)
        output_tokens = self.count_tokens(output_text_est, model_config.provider, model_config.model_name)
        output_cost = (output_tokens / 1_000_000) * output_price_1m

        # Image Cost
        image_cost = 0.0
        # We need image data to calculate tiles, but if we only have paths/IDs here it's hard.
        # Assuming 'images' passed here are base64 strings or we skip accurate tile calc for now
        # and use a default 'average' image cost if data is missing.
        for img_data in images:
            image_cost += self.calculate_image_cost(img_data, "image/jpeg", pc)

        total = input_cost + output_cost + image_cost

        # Apply discount
        discount = float(pc.get('discount_percent', 0))
        if discount > 0:
            total = total * (1 - (discount / 100))

        return total

    async def estimate_evaluation_cost(self, evaluation_id: str, db: Session) -> Dict[str, Any]:
        """
        Estimate total cost for an evaluation before running it.
        """
        eval_obj = db.query(Evaluation).filter(Evaluation.id == evaluation_id).first()
        if not eval_obj:
            raise ValueError("Evaluation not found")

        config = eval_obj.model_config
        if not config.pricing_config:
            return {"estimated_cost": 0.0, "details": "No pricing config"}

        # Get all images in dataset
        images = db.query(Image).filter(Image.dataset_id == eval_obj.dataset_id).all()
        total_images = len(images)

        if total_images == 0:
            return {"estimated_cost": 0.0, "details": "No images"}

        # Prepare prompts
        # Logic similar to run_evaluation_task to build prompt
        system_msg = eval_obj.system_message or ""
        question = eval_obj.question_text or ""

        # Combine multi-phase prompts if applicable
        if eval_obj.prompt_chain:
            combined_prompt = ""
            combined_system = ""
            for step in eval_obj.prompt_chain:
                combined_prompt += step.get("prompt", "") + "\n"
                combined_system += step.get("system_message", "") + "\n"
            input_text = combined_system + combined_prompt + question
        else:
            input_text = system_msg + "\n" + question

        # Estimate output length (hard to guess, assume 50 tokens per answer or max_tokens/2?)
        # Let's assume a reasonable default for estimation: 100 tokens
        output_est_text = "x" * 400 # ~100 tokens

        # Calculate cost for ONE image (average)
        # We need to peek at one image to get size for tile calc, or just use a default
        avg_image_cost = 0.0
        if images:
            # Try to get first image details if possible, or assume 1024x1024
            # Since we can't easily download all images here without taking too long,
            # we will assume a "Standard" image size for estimation if per_tile is used.
            # Or better, check 'file_size' in DB if that helps (it doesn't give dimensions).

            # Create a dummy 1024x1024 base64 image for estimation
            # 1024x1024 = 4 tiles (512x512)
            dummy_img_b64 = "iVBORw0KGgoAAAANSUhEUgAABAAAAAQCAYAAAAf8/9hAAAAAXNSR0IArs4c6Q..." # Not real
            # Actually, calculate_image_cost needs real b64 to open PIL.
            # If we pass a dummy string, PIL will fail.
            # We should refactor calculate_image_cost to accept dimensions optionally.

            # For now, let's use the 'per_image' fallback or a specific estimation method
            pc = config.pricing_config
            mode = pc.get('image_price_mode', 'per_image')

            if mode == 'per_image':
                avg_image_cost = float(pc.get('image_price_val', 0))
            elif mode == 'per_tile':
                # Assume 1024x1024 (4 tiles) -> 4*170 + 85 = 765 tokens
                input_price_1m = float(pc.get('input_price_per_1m', 0))
                avg_image_cost = (765 / 1_000_000) * input_price_1m
            else: # per_token
                # Assume 258 tokens
                input_price_1m = float(pc.get('input_price_per_1m', 0))
                avg_image_cost = (258 / 1_000_000) * input_price_1m

        # Calculate per-request cost
        single_req_cost = self.estimate_request_cost(input_text, output_est_text, [], config) # Text only
        single_req_cost += avg_image_cost

        total_est = single_req_cost * total_images

        return {
            "estimated_cost": round(total_est, 4),
            "image_count": total_images,
            "avg_cost_per_image": round(single_req_cost, 4),
            "details": {
                "input_tokens_est": self.count_tokens(input_text, config.provider, config.model_name),
                "output_tokens_est": 100,
                "pricing_used": config.pricing_config
            }
        }

    def calculate_actual_cost(self, usage_metadata: Dict[str, Any], pricing_config: Dict[str, Any]) -> float:
        """
        Calculate actual cost based on usage metadata and pricing config.
        usage_metadata: {prompt_tokens, completion_tokens, total_tokens}
        """
        if not pricing_config:
            return 0.0

        p_tokens = usage_metadata.get('prompt_tokens', 0)
        c_tokens = usage_metadata.get('completion_tokens', 0)

        in_price = float(pricing_config.get('input_price_per_1m', 0))
        out_price = float(pricing_config.get('output_price_per_1m', 0))

        cost = (p_tokens / 1_000_000 * in_price) + (c_tokens / 1_000_000 * out_price)

        # Image cost is usually included in prompt_tokens for OpenAI/Claude if configured correctly.
        # But for Gemini, images are separate if we use 'per_image' pricing.
        # However, usage_metadata from Gemini API might not include image tokens if they bill per image.
        # This part is tricky without exact provider knowledge of how they report usage.
        # For OpenAI/Claude, images ARE prompt tokens.
        # For Gemini, if 'per_image' mode is selected, we should add it?
        # But `generate_content` returns token counts.
        # If Gemini returns token counts that exclude image cost (because it's per image), we need to add it manually.
        # Let's assume usage_metadata reflects what the API returns.

        # If Gemini and pricing mode is 'per_image', we should add image cost per request (assuming 1 image per request for now).
        # But `calculate_actual_cost` receives just usage numbers. It doesn't know about images in the request.
        # We might need to pass image_count to this function.

        # For now, let's stick to token-based calculation + discount.
        # If the pricing config says 'per_image' for images, and we know there was an image...
        # We will refine this later. For now, rely on tokens if possible.

        discount = float(pricing_config.get('discount_percent', 0))
        if discount > 0:
            cost = cost * (1 - (discount / 100))

        return round(cost, 6)

# Singleton
_cost_service = None

def get_cost_service() -> CostEstimationService:
    global _cost_service
    if _cost_service is None:
        _cost_service = CostEstimationService()
    return _cost_service
