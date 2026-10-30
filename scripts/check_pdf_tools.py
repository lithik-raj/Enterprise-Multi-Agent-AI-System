import sys

libs = ['reportlab', 'fpdf', 'fpdf2', 'weasyprint', 'fitz', 'pypdf']
for lib in libs:
    try:
        __import__(lib)
        print(f"{lib}: AVAILABLE")
    except ImportError:
        print(f"{lib}: NOT AVAILABLE")
