# Evaluation Improvements - Ready for Local Testing

## Issues Fixed

### 1. **Vertex AI API Error** (CRITICAL BUG) ✅
**Problem**: All evaluations were failing with 100% failure rate
```
"message": "Please use a valid role: user, model."
```

**Fix**: Added missing `"role": "user"` field to Vertex AI API request
- **File**: `backend/api/v1/evaluations.py:211`
- **Change**: Added `"role": "user"` to contents array

### 2. **No True Background Processing** ✅
**Problem**: Evaluations used FastAPI BackgroundTasks which:
- Stop if user closes browser
- Are tied to the HTTP request lifecycle
- Don't survive server restarts

**Fix**: Implemented threading-based background jobs
- **File**: `backend/api/v1/evaluations.py:541-548`
- Creates daemon threads with their own event loops
- Evaluations continue even if user closes the page
- Independent of HTTP request lifecycle

### 3. **Sequential Processing** ✅
**Problem**: Images processed one-by-one, very slow for large datasets

**Fix**: Async parallelization with configurable concurrency
- **File**: `backend/api/v1/evaluations.py:400-469`
- Uses `asyncio.Semaphore` to limit concurrent API calls
- Processes multiple images in parallel
- Respects API rate limits via concurrency setting

## New Features

### 1. **Configurable Concurrency**
Control how many API calls run in parallel per evaluation.

**Backend**:
- Added `concurrency` field to `ModelConfig` model (default: 3)
- **File**: `backend/models/evaluation.py:19`

**Frontend**:
- Added concurrency input to model config form
- Range: 1-10 parallel calls
- **Files**:
  - `frontend/src/app/features/models/models.component.ts:78-84`
  - `frontend/src/app/core/services/evaluations.service.ts:34`

**Usage**: Higher concurrency = faster evaluations, but:
- Gemini: Max 10/sec recommended
- OpenAI: Depends on tier (check rate limits)
- Anthropic: Depends on tier

### 2. **Better Progress Tracking**
- Real-time progress updates during parallel processing
- Accurate counts even with concurrent execution

### 3. **Improved Error Reporting**
- Per-image error tracking
- Detailed failure messages
- Distinguishes between partial success and total failure

## Changes Summary

### Backend Files Modified

1. **`backend/api/v1/evaluations.py`**
   - Fixed Vertex AI role field (line 211)
   - Added asyncio and threading imports
   - Refactored evaluation to use async parallelization
   - Added `run_evaluation_in_thread` wrapper function
   - Removed `BackgroundTasks` dependency from endpoint
   - Uses `asyncio.Semaphore` for concurrency control

2. **`backend/models/evaluation.py`**
   - Added `concurrency` column to `ModelConfig` (default: 3)

### Frontend Files Modified

1. **`frontend/src/app/features/models/models.component.ts`**
   - Added concurrency input field to form
   - Default value: 3
   - Min: 1, Max: 10

2. **`frontend/src/app/core/services/evaluations.service.ts`**
   - Added `concurrency` to `CreateModelConfig` interface

## Testing Instructions

### Prerequisites
```bash
# Start local database
docker-compose up -d db

# Activate conda environment
conda activate multiprompt-sandbox

# Start backend
cd backend
uvicorn main:app --reload

# Start frontend (in new terminal)
cd frontend
npm start
```

### Test Scenarios

#### Test 1: Verify Vertex AI Fix
1. Create a model config with Gemini (leave API key empty)
2. Make sure you have annotated images
3. Run an evaluation
4. **Expected**: Should process images successfully (not 100% failure)
5. **Check logs**: No more "Please use a valid role" errors

#### Test 2: Test Background Processing
1. Start an evaluation with 10+ images
2. **Close the browser tab** immediately
3. Wait 30 seconds
4. Open the evaluations page again
5. **Expected**: Evaluation still progressing/completed
6. **Verify**: Status shows progress, not stuck at 0%

#### Test 3: Test Parallelization
1. Create model config with **concurrency = 1**
2. Run evaluation, note the time to complete
3. Create another model config with **concurrency = 5**
4. Run evaluation on same dataset, note the time
5. **Expected**: Higher concurrency = faster completion
6. **Typical speed**:
   - Concurrency 1: ~2-3 seconds per image
   - Concurrency 5: ~0.5 seconds per image

#### Test 4: Test Concurrency Limits
1. Create model config with **concurrency = 10**
2. Run evaluation with 20+ images
3. **Monitor**: Check that only 10 requests run concurrently
4. **Watch logs**: Should see "Processed image X/Y" messages
5. **Expected**: Completes without rate limit errors

### Verification Checklist

- [ ] Evaluations complete successfully (not 100% failure)
- [ ] Evaluations continue after closing browser
- [ ] Higher concurrency = faster processing
- [ ] Concurrency field appears in model config form
- [ ] Progress updates correctly during evaluation
- [ ] Detailed error messages if failures occur
- [ ] Logs show parallel processing (multiple images at once)

### Known Limitations

1. **Database Migration**: The `concurrency` column needs to be added to existing databases
   - **For Cloud**: Migration will run automatically on deploy
   - **For Local**: Run `alembic upgrade head` or manually add column

2. **Existing Model Configs**: Will have `concurrency = NULL`
   - Code defaults to 3 if null: `getattr(model_config, 'concurrency', 3)`
   - Edit and resave to set explicit value

3. **Progress During Parallel**: Progress updates may appear non-linear
   - Multiple images complete at once
   - Normal behavior with parallelization

## Performance Expectations

### Before (Sequential)
- 10 images × 2 seconds = **20 seconds total**
- 100 images × 2 seconds = **200 seconds (3.3 minutes)**

### After (Concurrency = 5)
- 10 images ÷ 5 parallel × 2 seconds = **4 seconds total**
- 100 images ÷ 5 parallel × 2 seconds = **40 seconds**

### After (Concurrency = 10)
- 10 images ÷ 10 parallel × 2 seconds = **2 seconds total**
- 100 images ÷ 10 parallel × 2 seconds = **20 seconds**

**Note**: Actual times depend on API latency and response speed.

## Deployment Notes

When ready to deploy (after local testing):
1. Commit changes
2. Push to trigger Cloud Build
3. Migration will auto-run to add `concurrency` column
4. Update existing model configs to set concurrency value

## Questions to Answer During Testing

1. **Does the Vertex AI fix work?**
   - Are evaluations succeeding instead of failing?

2. **Do background jobs persist?**
   - Can you close the browser and evaluations continue?

3. **Is parallelization faster?**
   - Compare evaluation times with different concurrency values

4. **Any new errors?**
   - Check logs for unexpected issues

## Rollback Plan

If issues occur:
```bash
# Revert backend changes
git checkout backend/api/v1/evaluations.py backend/models/evaluation.py

# Revert frontend changes
git checkout frontend/src/app/features/models/models.component.ts
git checkout frontend/src/app/core/services/evaluations.service.ts
```

---

**Status**: ✅ Code complete, ready for local testing
**Next Step**: Test locally, then commit and deploy if successful
