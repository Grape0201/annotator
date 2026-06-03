import os
import yaml
import click

@click.group()
def main():
    """Annotator - PDF generation and text annotation tool."""
    pass

@click.command()
@click.argument('input_file', type=click.Path(exists=True))
@click.option('--config', '-c', type=click.Path(exists=True), help='Path to annotation.yaml configuration file.')
@click.option('--output', '-o', default='output.pdf', help='Path to output PDF file.')
def render(input_file, config, output):
    """Render a text file as a PDF with annotations."""
    from .renderer import render_pdf
    
    # Read input file
    with open(input_file, 'r', encoding='utf-8') as f:
        source_text = f.read()
        
    # Read config/annotations YAML if provided
    config_data = {}
    if config:
        with open(config, 'r', encoding='utf-8') as f:
            config_data = yaml.safe_load(f) or {}
            
    filename = os.path.basename(input_file)
    render_pdf(source_text, config_data, output, filename)

@click.command()
@click.option('--host', default='127.0.0.1', help='Host to run the server on.')
@click.option('--port', default=8000, type=int, help='Port to run the server on.')
def start_server(host, port):
    """Start the Web API and preview UI server."""
    import uvicorn
    # Import the FastAPI app from server
    from .server import app
    print(f"Starting server on http://{host}:{port}...")
    uvicorn.run(app, host=host, port=port)

@click.command(name='download-font')
def download_font():
    """Pre-download and cache the monospace CJK font (M PLUS 1 Code) for offline usage."""
    import os
    from .renderer import get_cache_dir, ensure_font_loaded
    
    cache_dir = get_cache_dir()
    font_path = os.path.join(cache_dir, "MPLUS1Code-Regular.ttf")
    
    if os.path.exists(font_path):
        click.echo(f"Font is already cached at: {font_path}")
        return
        
    click.echo("Downloading monospace CJK font...")
    font_name = ensure_font_loaded()
    if font_name:
        click.echo(f"Success: Font downloaded and cached at: {font_path}")
    else:
        raise click.ClickException("Failed to download or register the font.")

# Register commands
main.add_command(render)
main.add_command(start_server)
main.add_command(download_font)

if __name__ == '__main__':
    main()

