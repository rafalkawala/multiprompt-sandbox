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

### Option 1: Using Cloud SQL Admin API (Recommended for Infrastructure-as-Code)
Google Cloud SQL for PostgreSQL has pgvector available as a database flag. However, the extension still needs to be enabled manually in the database.

**After deploying Cloud SQL:**
1. Connect to the database (via Cloud SQL Proxy or Private IP)
2. Run: `CREATE EXTENSION IF NOT EXISTS vector;`
3. Run Alembic migrations: `alembic upgrade head`

### Option 2: Enable via Cloud SQL Console
1. Navigate to Cloud SQL instance in GCP Console
2. Go to **Databases** tab
3. Select your database
4. Enable the `vector` extension (if available in the UI)

### Option 3: Via Terraform Provisioner (Not Recommended)
While you could use a Terraform `null_resource` with a `local-exec` provisioner to run the SQL command, this is generally not recommended for production as it requires:
- Database credentials in Terraform state
- Network connectivity from the Terraform runner to the database

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
