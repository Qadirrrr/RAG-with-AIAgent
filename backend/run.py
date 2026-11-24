import os
import sys
import uvicorn

if __name__ == "__main__":
    current_dir = os.path.dirname(os.path.abspath(__file__))
    sys.path.insert(0, current_dir)
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)

