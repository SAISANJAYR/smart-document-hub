# Use the official lightweight Python image
FROM python:3.11-slim

# Set the working directory inside the container
WORKDIR /app

# Copy the requirements file first (to leverage Docker cache)
COPY requirements.txt .

# Install uv for blazingly fast dependency resolution
RUN pip install uv

# Install dependencies using uv to avoid pip backtracking loops
RUN uv pip install --system --no-cache -r requirements.txt

# Copy the rest of the application code
COPY . .

# Expose port 8000 for the FastAPI server
EXPOSE 8000

# Start Uvicorn when the container launches
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
