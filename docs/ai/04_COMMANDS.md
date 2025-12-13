# Common Commands

## Environment Setup
```bash
conda activate multiprompt-sandbox
cp .env.example .env
# Edit .env with your keys
```

## Backend
```bash
# Install Dependencies
cd backend
pip install -r requirements.txt

# Run Local Server
uvicorn main:app --reload

# Run Tests
pytest

# Admin User Setup
python scripts/seed_admin.py
```

## Frontend
```bash
# Install Dependencies
cd frontend
pnpm install

# Run Development Server
pnpm start
# or
ng serve
```

## Database
```bash
# Start Local DB
docker-compose up -d db

# Run Migrations
cd backend
alembic upgrade head

# Create Migration
alembic revision --autogenerate -m "description"
```

## Infrastructure
```bash
cd infrastructure
terraform init
terraform plan
terraform apply
```
**Note:** Use Terraform for GCP resources. Do not use `gcloud` manually for persistent resources.
