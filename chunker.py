import os
from pypdf import PdfReader
from langchain_text_splitters import RecursiveCharacterTextSplitter

# Define your folders
PAPERS_FOLDER = "research papers"
OUTPUT_FOLDER = "chunks_output"

os.makedirs(OUTPUT_FOLDER, exist_ok=True)

# Initialize the text splitter
text_splitter = RecursiveCharacterTextSplitter(
    chunk_size=1000,
    chunk_overlap=200,
    length_function=len,
)

def extract_text_from_pdf(pdf_path):
    reader = PdfReader(pdf_path)
    text = ""
    for page in reader.pages:
        extracted = page.extract_text()
        if extracted:
            text += extracted + "\n"
    return text

# Loop through all PDFs in the research paper folder
for filename in os.listdir(PAPERS_FOLDER):
    if filename.endswith(".pdf"):
        pdf_path = os.path.join(PAPERS_FOLDER, filename)
        print(f"Processing: {filename}")
        
        # 1. Extract text
        raw_text = extract_text_from_pdf(pdf_path)
        
        # 2. Split text into chunks
        chunks = text_splitter.split_text(raw_text)
        print(f"-> Created {len(chunks)} chunks.")
        
        # 3. Save chunks to a file in the output folder
        base_name = os.path.splitext(filename)[0]
        output_file_path = os.path.join(OUTPUT_FOLDER, f"{base_name}_chunks.txt")
        
        with open(output_file_path, "w", encoding="utf-8") as f:
            for i, chunk in enumerate(chunks):
                f.write(f"--- CHUNK {i+1} ---\n")
                f.write(chunk + "\n\n")
                
        print(f"-> Saved to {output_file_path}\n")

print("Chunking and saving complete!")