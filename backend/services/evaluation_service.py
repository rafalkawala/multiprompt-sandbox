
import asyncio
import base64
import json
import structlog
import math
import os
import threading
import time
from datetime import datetime
from typing import List, Optional, Dict, Any

from sqlalchemy.orm import Session
from sqlalchemy.sql.expression import func

from core.database import SessionLocal
from core.prompt_config import get_system_prompt
from core.prompt_utils import substitute_variables
from models.evaluation import Evaluation, EvaluationResult
from models.image import Image, Annotation
from schemas.evaluation import EvaluationCreate, EvaluationResponse
from services.llm_service import get_llm_service
from services.storage_service import get_storage_provider
from services.cost_estimation_service import get_cost_service
from core.http_client import HttpClient
from dataclasses import dataclass

@dataclass
class ImageEvalData:
    id: str
    dataset_id: str
    filename: str
    storage_path: str
    ground_truth: Optional[Dict[str, Any]]

logger = structlog.get_logger(__name__)

class EvaluationService:
    def __init__(self, db: Session):
        self.db = db

    async def get_image_data(self, storage_path: str) -> tuple:
        """Get image data and mime type from storage path (GCS or local)
        Returns: (image_data_base64, mime_type)
        """
        storage = get_storage_provider()
        ext = os.path.splitext(storage_path)[1].lower()
        mime_types = {'.jpg': 'image/jpeg', '.jpeg': 'image/jpeg', '.png': 'image/png', '.gif': 'image/gif', '.webp': 'image/webp'}
        mime_type = mime_types.get(ext, 'image/jpeg')
        try:
            image_bytes = await storage.download(storage_path)
            image_data = base64.standard_b64encode(image_bytes).decode('utf-8')
            return image_data, mime_type
        except Exception as e:
            logger.error(f"Failed to download image {storage_path}: {e}")
            raise

    async def preload_images(self, images: List[ImageEvalData]) -> dict:
        """Pre-load all images in parallel for faster evaluation
        Returns: dict mapping image_id -> (base64_data, mime_type)
        """
        image_cache = {}

        async def load_image(image: ImageEvalData):
            try:
                image_data, mime_type = await self.get_image_data(image.storage_path)
                return image.id, (image_data, mime_type)
            except Exception as e:
                logger.error(f"Failed to preload image {image.id} (dataset: {image.dataset_id}, filename: {image.filename}, storage_path: {image.storage_path}): {e}")
                return image.id, None

        results = await asyncio.gather(*[load_image(img) for img in images])
        for img_id, data in results:
            if data:
                image_cache[img_id] = data
        logger.info(f"Preloaded {len(image_cache)}/{len(images)} images into cache")
        return image_cache

    def parse_answer(self, response: str, question_type: str):
        """Parse model response based on question type"""
        response_lower = response.lower().strip()
        if question_type == 'binary':
            if any(word in response_lower for word in ['yes', 'true', '1']):
                return {'value': True}
            elif any(word in response_lower for word in ['no', 'false', '0']):
                return {'value': False}
            return {'value': None, 'raw': response}
        elif question_type == 'count':
            import re
            numbers = re.findall(r'\d+', response)
            if numbers:
                return {'value': int(numbers[0])}
            return {'value': None, 'raw': response}
        elif question_type == 'multiple_choice':
            return {'value': response.strip()}
        else:
            return {'value': response.strip()}

    def check_answer(self, parsed: dict, ground_truth: dict, question_type: str) -> bool:
        """Check if answer matches ground truth"""
        if parsed.get('value') is None or ground_truth is None:
            return False
        if question_type in ['binary', 'count']:
            return parsed.get('value') == ground_truth.get('value')
        else:
            return str(parsed.get('value', '')).lower().strip() == str(ground_truth.get('value', '')).lower().strip()

    async def run_evaluation_task(self, evaluation_id: str):
        """Background task to run evaluation"""
        # We create a new session here because this runs in a background thread/task
        db = SessionLocal()
        try:
            evaluation = db.query(Evaluation).filter(Evaluation.id == evaluation_id).first()
            if not evaluation:
                return

            evaluation.status = 'running'
            evaluation.started_at = datetime.utcnow()
            db.commit()

            pricing_config = evaluation.model_config.pricing_config or {}
            model_config_data = {
                'provider': evaluation.model_config.provider,
                'api_key': evaluation.model_config.api_key,
                'auth_type': evaluation.model_config.auth_type,
                'model_name': evaluation.model_config.model_name,
                'temperature': evaluation.model_config.temperature,
                'max_tokens': evaluation.model_config.max_tokens,
                'pricing_config': pricing_config,
                'concurrency': getattr(evaluation.model_config, 'concurrency', 3),
                'retry_config': evaluation.model_config.retry_config
            }

            project_data = {
                'question_type': evaluation.project.question_type,
                'question_options': evaluation.project.question_options,
                'question_text': evaluation.project.question_text
            }

            query = db.query(Image).join(Annotation).filter(
                Image.dataset_id == evaluation.dataset_id,
                Image.processing_status != 'failed'
            )

            if evaluation.selection_config:
                mode = evaluation.selection_config.get('mode', 'all')
                if mode == 'random_count':
                    limit = evaluation.selection_config.get('count', 0)
                    if limit > 0:
                        query = query.order_by(func.random()).limit(limit)
                elif mode == 'random_percent':
                    percent = evaluation.selection_config.get('percent', 0)
                    if percent > 0:
                        total_count = db.query(Image).join(Annotation).filter(
                            Image.dataset_id == evaluation.dataset_id,
                            Image.processing_status != 'failed'
                        ).count()
                        limit = math.ceil((total_count * percent) / 100)
                        query = query.order_by(func.random()).limit(limit)
                elif mode == 'manual':
                    image_ids = evaluation.selection_config.get('image_ids', [])
                    if image_ids:
                        query = query.filter(Image.id.in_(image_ids))
                        logger.info(f"Evaluation {evaluation_id}: Manual selection mode with {len(image_ids)} image IDs")

            image_objects = query.all()
            evaluation.total_images = len(image_objects)
            db.commit()

            if not image_objects:
                evaluation.status = 'failed'
                evaluation.error_message = 'No annotated images in dataset (or selection criteria matched none)'
                db.commit()
                return

            images: List[ImageEvalData] = []
            for img in image_objects:
                images.append(ImageEvalData(
                    id=str(img.id),
                    dataset_id=str(img.dataset_id),
                    filename=img.filename,
                    storage_path=img.storage_path,
                    ground_truth=img.annotation.answer_value
                ))

            logger.info(f"Evaluation {evaluation_id}: Selected {len(images)} images from dataset {evaluation.dataset_id}")

            if evaluation.prompt_chain and len(evaluation.prompt_chain) > 0:
                steps = evaluation.prompt_chain
                logger.info(f"Evaluation {evaluation_id}: Using multi-phase prompting with {len(steps)} steps")
            else:
                if evaluation.system_message:
                    system_message = evaluation.system_message
                else:
                    system_message = get_system_prompt(
                        project_data['question_type'],
                        project_data['question_options'] if project_data['question_type'] == 'multiple_choice' else None
                    )
                if evaluation.question_text:
                    prompt = evaluation.question_text
                else:
                    prompt = project_data['question_text']
                steps = [{
                    "step_number": 1,
                    "system_message": system_message,
                    "prompt": prompt
                }]
                logger.info(f"Evaluation {evaluation_id}: Using legacy single-prompt mode")

            db.close()

            logger.info(f"Evaluation {evaluation_id}: Preloading {len(images)} images...")
            image_cache = await self.preload_images(images)

            if len(image_cache) == 0:
                db = SessionLocal()
                try:
                    eval_obj = db.query(Evaluation).filter(Evaluation.id == evaluation_id).first()
                    if eval_obj:
                        eval_obj.status = 'failed'
                        eval_obj.error_message = 'Failed to load any images'
                        db.commit()
                finally:
                    db.close()
                return

            correct_count = 0
            failed_count = 0
            error_messages = []
            total_actual_cost = 0.0
            concurrency = model_config_data.get('concurrency', 3)
            semaphore = asyncio.Semaphore(concurrency)
            completed_count = 0
            task_start_time = time.time()
            cumulative_latency_ms = 0

            async def process_image(i: int, image: ImageEvalData):
                nonlocal correct_count, failed_count, error_messages, completed_count, total_actual_cost, cumulative_latency_ms

                async with semaphore:
                    task_db = SessionLocal()
                    try:
                        cached_data = image_cache.get(image.id)
                        if not cached_data:
                            raise Exception(f"Image {image.id} not found in cache")
                        image_data, mime_type = cached_data

                        step_results = []
                        outputs = {}
                        total_latency = 0
                        total_row_prompt_tokens = 0
                        total_row_completion_tokens = 0
                        total_row_cost = 0.0

                        for step in steps:
                            step_num = step['step_number']
                            system_message = step.get('system_message')
                            prompt_template = step['prompt']
                            prompt = substitute_variables(prompt_template, outputs)

                            start_time = time.time()
                            llm_service = get_llm_service()
                            response_text, token_count, usage_metadata = await llm_service.generate_content(
                                provider_name=model_config_data['provider'],
                                api_key=model_config_data['api_key'],
                                auth_type=model_config_data['auth_type'],
                                model_name=model_config_data['model_name'],
                                prompt=prompt,
                                image_data=image_data,
                                mime_type=mime_type,
                                system_message=system_message,
                                temperature=model_config_data['temperature'],
                                max_tokens=model_config_data['max_tokens'],
                                retry_config=model_config_data['retry_config']
                            )
                            latency = int((time.time() - start_time) * 1000)
                            total_latency += latency
                            outputs[step_num] = response_text

                            step_cost = 0.0
                            step_cost_details = {}
                            if model_config_data['pricing_config']:
                                step_cost = get_cost_service().calculate_actual_cost(
                                    usage_metadata,
                                    model_config_data['pricing_config'],
                                    has_image=bool(image_data),
                                    provider=model_config_data['provider']
                                )
                                step_cost_details = {'step_cost': step_cost}
                                total_actual_cost += step_cost
                                total_row_cost += step_cost
                                total_row_prompt_tokens += usage_metadata.get('prompt_tokens', 0)
                                total_row_completion_tokens += usage_metadata.get('completion_tokens', 0)

                            step_results.append({
                                "step_number": step_num,
                                "raw_output": response_text,
                                "latency_ms": latency,
                                "usage": usage_metadata,
                                "cost": step_cost_details,
                                "error": None
                            })

                        cumulative_latency_ms += total_latency
                        final_step_num = steps[-1]["step_number"]
                        final_output = outputs[final_step_num]
                        parsed = self.parse_answer(final_output, project_data['question_type'])
                        ground_truth = image.ground_truth
                        is_correct = self.check_answer(parsed, ground_truth, project_data['question_type'])
                        if is_correct:
                            correct_count += 1

                        result = EvaluationResult(
                            evaluation_id=evaluation_id,
                            image_id=image.id,
                            model_response=final_output,
                            parsed_answer=parsed,
                            ground_truth=ground_truth,
                            is_correct=is_correct,
                            step_results=step_results,
                            latency_ms=total_latency,
                            prompt_tokens=total_row_prompt_tokens,
                            completion_tokens=total_row_completion_tokens,
                            cost=total_row_cost,
                            token_count=total_row_prompt_tokens + total_row_completion_tokens
                        )
                        task_db.add(result)

                    except Exception as e:
                        failed_count += 1
                        error_msg = f"Image {image.filename}: {str(e)}"
                        error_messages.append(error_msg)
                        logger.error(f"Evaluation {evaluation_id}: Failed image {i+1}/{len(images)} - {error_msg}", exc_info=True)
                        result = EvaluationResult(
                            evaluation_id=evaluation_id,
                            image_id=image.id,
                            error=str(e),
                            step_results=step_results if 'step_results' in locals() and step_results else None
                        )
                        task_db.add(result)

                    current_eval = task_db.query(Evaluation).filter(Evaluation.id == evaluation_id).first()
                    if current_eval:
                        completed_count += 1
                        current_eval.processed_images = completed_count
                        current_eval.progress = int((completed_count / len(images)) * 100)
                        if not current_eval.results_summary:
                            current_eval.results_summary = {}
                        summary = dict(current_eval.results_summary) if current_eval.results_summary else {}
                        latest = summary.get('latest_images', [])
                        latest.append(f"{completed_count}/{len(images)}: {image.filename}")
                        if len(latest) > 5:
                            latest = latest[-5:]
                        summary['latest_images'] = latest

                        if completed_count >= concurrency:
                            remaining_images = len(images) - completed_count
                            if cumulative_latency_ms > 0:
                                avg_latency_seconds = (cumulative_latency_ms / 1000) / completed_count
                                eta_seconds = (avg_latency_seconds * remaining_images) / concurrency
                            else:
                                now = time.time()
                                elapsed_total = now - task_start_time
                                avg_wall_time = elapsed_total / completed_count
                                eta_seconds = avg_wall_time * remaining_images
                            summary['eta_seconds'] = round(eta_seconds, 1)
                        current_eval.results_summary = summary
                        task_db.commit()
                    task_db.close()

            await asyncio.gather(*[process_image(i, img) for i, img in enumerate(images)])

            db = SessionLocal()
            try:
                evaluation = db.query(Evaluation).filter(Evaluation.id == evaluation_id).first()
                if not evaluation:
                     logger.error(f"Evaluation {evaluation_id} disappeared during processing")
                     return

                total_processed = len(images)
                successful_count = total_processed - failed_count
                failure_rate = (failed_count / total_processed * 100) if total_processed > 0 else 0

                confusion_matrix = None
                if project_data['question_type'] == 'binary':
                    tp = tn = fp = fn = 0
                    results = db.query(EvaluationResult).filter(EvaluationResult.evaluation_id == evaluation.id).all()
                    for r in results:
                        if r.is_correct is None: continue
                        gt = r.ground_truth.get('value') if r.ground_truth else None
                        pred = r.parsed_answer.get('value') if r.parsed_answer else None
                        if gt is True and pred is True: tp += 1
                        elif gt is False and pred is False: tn += 1
                        elif gt is False and pred is True: fp += 1
                        elif gt is True and pred is False: fn += 1
                    confusion_matrix = {'tp': tp, 'tn': tn, 'fp': fp, 'fn': fn}

                FAILURE_THRESHOLD_PERCENT = 50
                if failure_rate > FAILURE_THRESHOLD_PERCENT:
                    evaluation.status = 'failed'
                    evaluation.error_message = f"Evaluation failed: {failure_rate:.1f}% predictions failed. Errors: {'; '.join(error_messages[:3])}"
                else:
                    evaluation.status = 'completed'

                evaluation.completed_at = datetime.utcnow()
                evaluation.accuracy = correct_count / successful_count if successful_count > 0 else 0
                evaluation.actual_cost = round(total_actual_cost, 4)

                total_prompt_tokens = 0
                total_completion_tokens = 0
                results = db.query(EvaluationResult).filter(EvaluationResult.evaluation_id == evaluation.id).all()
                for r in results:
                    if r.step_results:
                        for step in r.step_results:
                            usage = step.get('usage', {})
                            total_prompt_tokens += usage.get('prompt_tokens', 0)
                            total_completion_tokens += usage.get('completion_tokens', 0)

                evaluation.cost_details = {
                    'total_prompt_tokens': total_prompt_tokens,
                    'total_completion_tokens': total_completion_tokens,
                    'total_tokens': total_prompt_tokens + total_completion_tokens,
                    'total_cost': evaluation.actual_cost,
                    'average_cost_per_image': round(evaluation.actual_cost / total_processed, 6) if total_processed > 0 else 0
                }

                final_summary = dict(evaluation.results_summary) if evaluation.results_summary else {}
                final_summary.update({
                    'correct': correct_count,
                    'total': total_processed,
                    'successful': successful_count,
                    'failed': failed_count,
                    'failure_rate_percent': round(failure_rate, 2),
                    'accuracy_percent': round(evaluation.accuracy * 100, 2),
                    'confusion_matrix': confusion_matrix
                })
                if 'eta_seconds' in final_summary:
                    del final_summary['eta_seconds']
                evaluation.results_summary = final_summary
                db.commit()
                logger.info(f"Evaluation {evaluation_id} finished: status={evaluation.status}, accuracy={evaluation.accuracy:.2%}")

            except Exception as e:
                logger.error(f"Evaluation error: {str(e)}", exc_info=True)
                db.rollback()
                try:
                    evaluation = db.query(Evaluation).filter(Evaluation.id == evaluation_id).first()
                    if evaluation:
                        evaluation.status = 'failed'
                        evaluation.error_message = str(e)
                        db.commit()
                except:
                    pass
            finally:
                db.close()

        except Exception as e:
            logger.error(f"Evaluation setup error: {str(e)}", exc_info=True)
            if 'db' in locals(): db.close()
            db = SessionLocal()
            try:
                evaluation = db.query(Evaluation).filter(Evaluation.id == evaluation_id).first()
                if evaluation:
                    evaluation.status = 'failed'
                    evaluation.error_message = f"Setup error: {str(e)}"
                    db.commit()
            except:
                pass
            finally:
                db.close()

def run_evaluation_in_thread(evaluation_id: str):
    """Wrapper to run async evaluation task in a thread with its own event loop"""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        service = EvaluationService(None) # DB session managed inside task
        loop.run_until_complete(service.run_evaluation_task(evaluation_id))
    finally:
        try:
            loop.run_until_complete(HttpClient.close())
        except Exception as e:
            logger.error(f"Error closing HTTP client: {e}")
        loop.close()
