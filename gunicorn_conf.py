from multiprocessing import cpu_count

# Gunicorn config
bind = "0.0.0.0:5000"
workers = 1  # For simplicity, use just one worker
worker_class = "uvicorn.workers.UvicornWorker"  # Use Uvicorn worker for ASGI support
reload = True