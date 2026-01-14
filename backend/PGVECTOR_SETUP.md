# pgvector Setup Guide

## Overview
This project uses [pgvector](https://github.com/pgvector/pgvector) to store and query multimodal embeddings efficiently in PostgreSQL. Embeddings are stored as native vector types instead of JSON for optimal similarity search performance.

## Requirements

### Database
- **PostgreSQL 11+** (we use PostgreSQL 18)
- **pgvector extension** must be installed on the database

### Python
- `pgvector==0.3.6` (added to `requirements.txt`)

## Local Development Setup

### 1. Install Python Package
```bash
conda activate multiprompt-sandbox
pip install pgvector==0.3.6
```

### 2. Enable Extension in Database
The extension is automatically enabled via Alembic migration `bdb80060ab5g_enable_pgvector_extension.py`.

Run migrations:
```bash
cd backend
alembic upgrade head
```

This will:
1. Enable the `vector` extension (`bdb80060ab5g`)
2. Add the `embedding` column as `vector(1408)` to the `images` table (`bdb80060ab60`)

## Cloud SQL (GCP) Setup

### Automatic Setup via Alembic Migration ✅

The pgvector extension is **automatically enabled** by Alembic migration `bdb80060ab5g_enable_pgvector_extension.py` when you run:

```bash
alembic upgrade head
```

This runs automatically on Cloud Run startup (see `backend/Dockerfile` CMD).

### Prerequisites

**PostgreSQL Version:** 11+ (we use PostgreSQL 18)

**User Permissions:** The database user needs permission to create extensions. For Cloud SQL:

#### Option 1: Grant Superuser Role (Recommended for Automated Setup)

```bash
# Connect as postgres user
gcloud sql connect <instance-name> --user=postgres --quiet

# Grant superuser to your application user
ALTER USER mllm_sandbox_user WITH SUPERUSER;
```

#### Option 2: Pre-install Extension as Superuser (Manual Setup)

If you don't want to grant superuser permissions to the application user:

```bash
# Connect as postgres user
gcloud sql connect <instance-name> --user=postgres --quiet

# Manually create the extension
CREATE EXTENSION IF NOT EXISTS vector;

# Verify
SELECT extname, extversion FROM pg_extension WHERE extname = 'vector';
```

Then the Alembic migration will detect it's already installed and skip creation.

### Verification

You can verify pgvector setup before migrations:

```bash
# Set environment variable to enable verification
export VERIFY_PGVECTOR=1

# Run the verification script
python backend/scripts/verify_pgvector.py
```

Or in Cloud Run, add the environment variable:

```bash
gcloud run services update multiprompt-backend \
  --region=us-central1 \
  --set-env-vars=VERIFY_PGVECTOR=1
```

### Troubleshooting

**Error: "permission denied to create extension"**
- **Cause:** Database user doesn't have permission to create extensions
- **Solution:** Grant superuser role (see Option 1 above) or manually install extension (Option 2)

**Error: "could not open extension control file"**
- **Cause:** pgvector is not installed on the PostgreSQL server
- **Solution:** Cloud SQL for PostgreSQL 11+ includes pgvector. Verify your instance version and tier support it.

**Migrations succeed but vector column fails**
- **Cause:** Extension not enabled before vector column creation
- **Solution:** Check migration order. `bdb80060ab5g` must run before `bdb80060ab60`.

## Migration Details

### Migration Chain
```
bdb80060ab5f (annotation_import_jobs)
    ↓
bdb80060ab5g (enable pgvector extension)
    ↓
bdb80060ab60 (add embedding vector column)
```

### Embedding Specifications
- **Model**: `multimodalembedding@001` (Google Vertex AI)
- **Dimension**: 1408 (default output dimension)
- **Column Type**: `vector(1408)`
- **Nullable**: Yes (allows gradual rollout and soft failure)

## Usage in Code

### Model Definition
```python
from pgvector.sqlalchemy import Vector

class Image(Base):
    embedding = Column(Vector(1408), nullable=True)
```

### Storing Embeddings
```python
# Embeddings are automatically converted from Python lists
image.embedding = [0.1, 0.2, ..., 0.3]  # List of 1408 floats
db.commit()
```

### Similarity Search (Future)
```python
from pgvector.sqlalchemy import Vector

# L2 distance (Euclidean)
similar_images = db.query(Image).order_by(
    Image.embedding.l2_distance([0.1, 0.2, ..., 0.3])
).limit(10).all()

# Cosine distance
similar_images = db.query(Image).order_by(
    Image.embedding.cosine_distance([0.1, 0.2, ..., 0.3])
).limit(10).all()
```

## Deployment Checklist

- [ ] Ensure PostgreSQL 11+ is used
- [ ] Verify `pgvector` is available in Cloud SQL instance
- [ ] Enable `vector` extension: `CREATE EXTENSION IF NOT EXISTS vector;`
- [ ] Run Alembic migrations: `alembic upgrade head`
- [ ] Verify `images.embedding` column exists with type `vector(1408)`
- [ ] Test embedding generation pipeline

## Troubleshooting

### "extension 'vector' does not exist"
- **Cause**: pgvector extension not installed on PostgreSQL server
- **Solution**: Install pgvector on your PostgreSQL instance. For Cloud SQL, check if pgvector is supported for your PostgreSQL version.

### "dimension mismatch"
- **Cause**: Trying to insert embeddings with incorrect dimensions
- **Solution**: Ensure embeddings are exactly 1408 dimensions. Check the model output.

### "No module named 'pgvector'"
- **Cause**: Python package not installed
- **Solution**: `pip install pgvector==0.3.6` in the correct conda environment

## References

- [pgvector GitHub](https://github.com/pgvector/pgvector)
- [pgvector-python SQLAlchemy docs](https://github.com/pgvector/pgvector-python#sqlalchemy)
- [Google Cloud SQL pgvector support](https://cloud.google.com/sql/docs/postgres/extensions)
