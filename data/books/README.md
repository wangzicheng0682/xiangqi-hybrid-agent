# Chess Books Directory

Place your chess book PDFs here for RAG retrieval.

## Requirements

- Format: PDF (preferred), TXT, or DOCX
- Language: Chinese (traditional or simplified)
- Copyright: Ensure you have permission to use these materials

## Recommended Sources

### Public Domain Classics
- 《橘中秘》by 朱晋桢 (Ming Dynasty)
- 《梅花谱》by 王再越 (Qing Dynasty)
- 《适情雅趣》
- 《竹香斋》

### Modern Books
- Modern opening theory books
- Annotated game collections
- Strategy guides

## File Organization

```
books/
├── 古谱/
│   ├── 橘中秘.pdf
│   └── 梅花谱.pdf
├── 现代布局/
│   └── 顺炮布局详解.pdf
└── 棋手对局/
    └── 特级大师对局精选.pdf
```

## Vectorization

After adding books, run:
```bash
python scripts/vectorize_books.py
```

This will create:
- `data/vector_db/books.index` (FAISS index)
- `data/vector_db/books.meta` (metadata)

## Configuration

Update `config/settings.yaml`:
```yaml
rag:
  index_path: "data/vector_db/books.index"
  metadata_path: "data/vector_db/books.meta"
```
