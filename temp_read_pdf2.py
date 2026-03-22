import fitz
import os
import glob

# Find PDF files in docs directory
docs_dir = r'D:\xiangqi-hybrid-agent\docs'
pdf_files = glob.glob(os.path.join(docs_dir, "*.pdf"))

print("Found PDF files:")
for f in pdf_files:
    print(f"  - {os.path.basename(f)}")

# Read the NeurIPS paper
target_pdf = None
for f in pdf_files:
    if "NeurIPS" in f or "amortized" in f.lower():
        target_pdf = f
        break

if target_pdf:
    print(f"\nReading: {os.path.basename(target_pdf)}")
    doc = fitz.open(target_pdf)
    for i, page in enumerate(doc):
        if i < 5:  # Read first 5 pages
            print(f"\n{'='*60}")
            print(f"Page {i+1}")
            print('='*60)
            print(page.get_text())
    doc.close()
else:
    print("NeurIPS paper not found!")
