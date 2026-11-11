FROM python:3.12-slim
    # Or whatever version of Python we need to use for the image

WORKDIR /app

# Installs the dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY alembic.ini .
COPY alembic ./alembic
COPY backend ./backend

# Create a non-root user for security purposes
RUN useradd --create-home appuser && chown -R appuser /app
USER appuser

# Expose the port the application will listen on
EXPOSE 8000

# Define the command to run the application
CMD ["uvicorn", "backend.app.main:app", "--host", "0.0.0.0", "--port", "8000"]