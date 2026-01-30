from sqlalchemy.orm import declarative_base

# Create a new Base for tests to avoid conflicts with global Base
TestBase = declarative_base()
