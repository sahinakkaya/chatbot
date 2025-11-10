# Helper Scripts

## json_to_txt.py

Converts resume-data.json to a well-formatted text file optimized for RAG (Retrieval-Augmented Generation).

### Why TXT instead of JSON?

- **Simpler**: Easier to read and edit
- **Better semantic search**: Natural language text matches questions better
- **More maintainable**: No need for complex JSON structure
- **Direct**: What you write is what the AI sees

### Usage

**Default** (converts data/resume-data.json to data/resume-data.txt):
```bash
python scripts/json_to_txt.py
```

**Custom input file**:
```bash
python scripts/json_to_txt.py path/to/your/resume.json
```

**Custom input and output**:
```bash
python scripts/json_to_txt.py path/to/input.json path/to/output.txt
```

### What it does

The script converts structured JSON data into natural language paragraphs:

**JSON:**
```json
{
  "education": [{
    "school": "Istanbul Technical University",
    "degree": "Bachelor's Degree in Computer Engineering",
    "duration": "2017 - 2023"
  }]
}
```

**TXT:**
```
# EDUCATION

He graduated from Istanbul Technical University with a Bachelor's Degree
in Computer Engineering from 2017 - 2023 in İstanbul, Turkey with a GPA
of 2.99/4.00.
Relevant courses: Artificial Intelligence, Analysis of Algorithms...
```

### Generated Format

The text file includes:
- Personal information (name, title, location, contacts)
- About and summary sections
- Education with natural language formatting
- Work experience with job details
- Skills organized by category
- Projects with descriptions
- Interests and additional information

### Workflow

1. **Edit JSON** (structured, easy to maintain):
   ```bash
   nano data/resume-data.json
   ```

2. **Convert to TXT** (optimized for AI):
   ```bash
   python scripts/json_to_txt.py
   ```

3. **Deploy** (AI uses the TXT file):
   ```bash
   docker-compose restart ai-consumer
   ```

### Notes

- The script preserves UTF-8 characters (e.g., Ş, ı)
- Headers are markdown format (# SECTION, ## Subsection)
- Empty lines separate sections for better chunking
- Natural language repetition improves semantic search
- The generated TXT file is what the RAG system actually uses
