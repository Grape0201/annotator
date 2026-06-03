import os
import tempfile
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field, ValidationError

app = FastAPI(title="Annotator API", description="API to generate annotated PDFs from text.")

# Define request model
class RenderRequest(BaseModel):
    text: str = Field(..., description="The plain text content to render.")
    config_yaml: str = Field(default="", description="Annotation settings and items in raw YAML string format.")
    filename: str | None = Field("document.txt", description="Name of the file shown in the header.")

# Path for static assets
STATIC_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")

@app.post("/api/render")
def render_api(request: RenderRequest):
    """
    Generate an annotated PDF from plain text and configuration.
    Returns the binary PDF file.
    """
    from .config import RenderConfig
    from .renderer import render_pdf
    import yaml
    
    # Parse YAML configuration server-side to allow offline client execution without js-yaml
    try:
        config_data = yaml.safe_load(request.config_yaml) or {}
        config = RenderConfig.model_validate(config_data)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"YAML syntax error: {str(e)}")
    except ValidationError as exc:
        raise HTTPException(status_code=400, detail=f"Configuration validation failed: {exc}")

    
    # Create a temporary file to hold the output PDF
    temp_dir = tempfile.gettempdir()
    temp_pdf_path = os.path.join(temp_dir, next(tempfile._get_candidate_names()) + ".pdf")
    
    try:
        # Call the renderer
        render_pdf(
            source_text=request.text,
            config=config,
            output_path=temp_pdf_path,
            filename=request.filename if request.filename else "output.pdf"
        )
        
        # Return FileResponse. Standard FastAPI FileResponse doesn't delete the file automatically.
        # We can write a custom subclass of FileResponse or clean up via a background task,
        # but since it's in the system temp directory, the OS will clean it up periodically.
        # However, for robustness, we can clean it up using a background task!
        from fastapi import BackgroundTasks
        background_tasks = BackgroundTasks()
        background_tasks.add_task(os.remove, temp_pdf_path)
        
        return FileResponse(
            path=temp_pdf_path,
            media_type="application/pdf",
            filename="annotated.pdf",
            background=background_tasks
        )
    except Exception as e:
        if os.path.exists(temp_pdf_path):
            try:
                os.remove(temp_pdf_path)
            except:  # noqa: E722
                pass
        raise HTTPException(status_code=500, detail=f"PDF Generation failed: {str(e)}")

@app.get("/")
def get_ui():
    """Serves the preview UI HTML page."""
    index_path = os.path.join(STATIC_DIR, "index.html")
    if not os.path.exists(index_path):
        raise HTTPException(status_code=404, detail="Web UI not found. Build static/index.html first.")
    return FileResponse(index_path)
