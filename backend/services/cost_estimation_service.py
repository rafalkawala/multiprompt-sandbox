import structlog
import base64
from typing import Optional, Dict, List, Any, Union
from sqlalchemy.orm import Session

from models.evaluation import ModelConfig, Evaluation
from models.image import Image
from infrastructure.llm.openai import OpenAIProvider
from infrastructure.llm.anthropic import AnthropicProvider
from infrastructure.llm.gemini import GeminiProvider
from infrastructure.llm.vertex import VertexAIProvider

logger = structlog.get_logger(__name__)

class CostEstimationService:
    """Service for estimating and calculating costs for LLM operations"""

    def __init__(self):
        self._providers = {
            "openai": OpenAIProvider(),
            "anthropic": AnthropicProvider(),
            "gemini": GeminiProvider(),
            "vertex": VertexAIProvider()
        }

    def _get_provider(self, provider_name: str):
        provider = self._providers.get(provider_name)
        if not provider:
            # Fallback or raise? For estimation, maybe safe default or raise.
            raise ValueError(f"Unknown provider for cost estimation: {provider_name}")
        return provider

    async def estimate_evaluation_cost(self, evaluation_id: str, db: Session) -> Dict[str, Any]:
        """
        Estimate total cost for an evaluation before running it.
        Uses sampling (up to 5 images) to estimate average image cost.
        """
        from services.storage_service import get_storage_provider

        eval_obj = db.query(Evaluation).filter(Evaluation.id == evaluation_id).first()
        if not eval_obj:
            raise ValueError("Evaluation not found")

        config = eval_obj.model_config
        if not config.pricing_config:
            return {"estimated_cost": 0.0, "details": "No pricing config"}

        provider = self._get_provider(config.provider)

        # Get all images in dataset
        images = db.query(Image).filter(Image.dataset_id == eval_obj.dataset_id).all()
        total_images = len(images)

        if total_images == 0:
            return {"estimated_cost": 0.0, "details": "No images"}

        # Prepare prompts
        system_msg = eval_obj.system_message or ""
        question = eval_obj.question_text or ""

        if eval_obj.prompt_chain:
            combined_prompt = ""
            combined_system = ""
            for step in eval_obj.prompt_chain:
                combined_prompt += step.get("prompt", "") + "\n"
                combined_system += step.get("system_message", "") + "\n"
            input_text = combined_system + combined_prompt + question
        else:
            input_text = system_msg + "\n" + question

        output_est_text = "x" * 400  # ~100 tokens

        # 1. Calculate Text Cost (Base per request)
        text_cost = provider.estimate_cost(
            input_text=input_text,
            output_est_text=output_est_text,
            images=[],
            pricing_config=config.pricing_config
        )

        # 2. Calculate Average Image Cost via Sampling
        avg_image_cost = 0.0
        sample_size = min(5, total_images)
        sample_images = images[:sample_size]
        
        total_sample_cost = 0.0
        valid_samples = 0
        storage = get_storage_provider()

        for img in sample_images:
            try:
                img_data = await storage.download(img.storage_path)
                img_b64 = base64.b64encode(img_data).decode('utf-8')
                
                # Estimate cost for this single image (no text, as text is added separately)
                cost = provider.estimate_cost(
                    input_text="", 
                    output_est_text="", 
                    images=[img_b64], 
                    pricing_config=config.pricing_config
                )
                total_sample_cost += cost
                valid_samples += 1
            except Exception as e:
                logger.warning(f"Failed to sample image {img.id} for cost estimation: {e}")

        if valid_samples > 0:
            avg_image_cost = total_sample_cost / valid_samples
        else:
            # Fallback: estimate with a dummy placeholder if provider supports it logic, 
            # or just 0 if we can't get data.
            # Ideally we'd pass a dummy b64, but that's heavy. 
            # Let's rely on provider handling empty images as 0 cost, which is fine if download fails.
            pass

        # Total Calculation
        single_req_total = text_cost + avg_image_cost
        total_est = single_req_total * total_images

        return {
            "estimated_cost": round(total_est, 4),
            "image_count": total_images,
            "avg_cost_per_image": round(avg_image_cost, 6),
            "details": {
                "text_cost_per_req": round(text_cost, 6),
                "pricing_used": config.pricing_config,
                "sampled_images": valid_samples
            }
        }

    def calculate_actual_cost(
        self,
        usage_metadata: Dict[str, Any],
        pricing_config: Dict[str, Any],
        has_image: bool = False,
        provider: str = 'openai'
    ) -> float:
        """
        Calculate actual cost based on usage metadata and pricing config.
        Delegates to the specific provider implementation.
        """
        if not pricing_config:
            return 0.0

        try:
            prov_instance = self._get_provider(provider)
            return prov_instance.calculate_actual_cost(usage_metadata, pricing_config, has_image)
        except Exception as e:
            logger.error(f"Error calculating actual cost with provider {provider}: {e}")
            return 0.0

# Singleton
_cost_service = None

def get_cost_service() -> CostEstimationService:
    global _cost_service
    if _cost_service is None:
        _cost_service = CostEstimationService()
    return _cost_service
