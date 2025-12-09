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
            # Estimate tokens for image (Claude approx: 258 tokens per image)
            tokens = 258
            # price_val is cost per 1M tokens
            input_price_1m = float(pricing_config.get('input_price_per_1m', 0))
            return (tokens / 1_000_000) * input_price_1m

        elif mode == 'per_tile':
            # OpenAI style: Low detail = 85 tokens. High detail = tiles * 170 + 85.
            # We need image dimensions to calculate tiles.
            try:
                # Decode image to get dimensions
                img_bytes = base64.b64decode(image_data_b64)
                with PILImage.open(io.BytesIO(img_bytes)) as img:
                    width, height = img.size

                # OpenAI tile calculation (High detail):
                # Images are scaled to fit within 2048x2048,
                # then shortest side is scaled to 768px,
                # then divided into 512px tiles

                # Simplified approximation:
                h_tiles = math.ceil(width / 512)
                v_tiles = math.ceil(height / 512)
                total_tiles = h_tiles * v_tiles

                tokens = (total_tiles * 170) + 85

                # price_val is input price per 1M tokens
                input_price_1m = float(pricing_config.get('input_price_per_1m', 0))
                return (tokens / 1_000_000) * input_price_1m

            except Exception as e:
                logger.warning(f"Failed to calculate image tiles: {e}. Using fallback cost.")
                # Fallback: assume 1024x1024 image (4 tiles) = 765 tokens
                input_price_1m = float(pricing_config.get('input_price_per_1m', 0))
                return (765 / 1_000_000) * input_price_1m

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

        # Estimate output length (assume 100 tokens)
        output_est_text = "x" * 400  # ~100 tokens

        # Calculate average image cost
        avg_image_cost = 0.0
        pc = config.pricing_config
        mode = pc.get('image_price_mode', 'per_image')

        if mode == 'per_image':
            avg_image_cost = float(pc.get('image_price_val', 0))
        elif mode == 'per_tile':
            # Assume 1024x1024 (4 tiles) -> 4*170 + 85 = 765 tokens
            input_price_1m = float(pc.get('input_price_per_1m', 0))
            avg_image_cost = (765 / 1_000_000) * input_price_1m
        else:  # per_token
            # Assume 258 tokens
            input_price_1m = float(pc.get('input_price_per_1m', 0))
            avg_image_cost = (258 / 1_000_000) * input_price_1m

        # Calculate per-request cost (text only + average image cost)
        single_req_cost = self.estimate_request_cost(input_text, output_est_text, [], config)
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

    def calculate_actual_cost(
        self,
        usage_metadata: Dict[str, Any],
        pricing_config: Dict[str, Any],
        has_image: bool = False,
        provider: str = None
    ) -> float:
        """
        Calculate actual cost based on usage metadata and pricing config.

        Args:
            usage_metadata: {prompt_tokens, completion_tokens, total_tokens}
            pricing_config: Pricing configuration dict
            has_image: Whether the request included an image
            provider: Provider name (gemini, openai, anthropic) to determine image cost handling

        Returns:
            Total cost for the request
        """
        if not pricing_config:
            return 0.0

        p_tokens = usage_metadata.get('prompt_tokens', 0)
        c_tokens = usage_metadata.get('completion_tokens', 0)

        in_price = float(pricing_config.get('input_price_per_1m', 0))
        out_price = float(pricing_config.get('output_price_per_1m', 0))

        # Token-based cost
        cost = (p_tokens / 1_000_000 * in_price) + (c_tokens / 1_000_000 * out_price)

        # Image cost handling
        # OpenAI: Image tokens are included in prompt_tokens (tile-based)
        # Anthropic: Image tokens are included in prompt_tokens
        # Gemini: Depends on mode - 'per_image' is separate, token-based may be included
        if has_image:
            image_mode = pricing_config.get('image_price_mode', 'per_image')

            # For per_image mode (typically Gemini), add the fixed per-image cost
            # This is needed because Gemini may not include image cost in token counts
            if image_mode == 'per_image':
                image_cost = float(pricing_config.get('image_price_val', 0))
                cost += image_cost

            # For per_tile (OpenAI) and per_token (Anthropic),
            # the cost is already included in prompt_tokens by the API

        # Apply discount
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
