# RAG Server - Multi-Index Vector Store

A scalable, fault-tolerant RAG (Retrieval-Augmented Generation) server that accepts input files (PDFs, tables, images) and answers queries based on those files. Built with FastAPI, MongoDB, Redis, Qdrant, and Google Gemini.

## Features

- **Multi-Index Vector Storage**: Uses Qdrant with separate collections for different document types (PDF, DOCX, XLSX, CSV, TXT, Images)
- **Federated Search**: Searches across all collections and merges results for comprehensive answers
- **Document Processing**: Supports PDF, DOCX, XLSX, CSV, TXT, and image files (PNG, JPG, JPEG)
- **LLM Integration**: Google Gemini (primary), OpenAI GPT (fallback), Ollama (local fallback)
- **Scalable Architecture**: FastAPI backend with MongoDB and Redis
- **Docker Deployment**: Complete containerized setup with Docker Compose
- **Monitoring & Logging**: Comprehensive health checks and metrics
- **Fault Tolerance**: Graceful fallbacks and error handling

## Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   FastAPI App   │    │   Qdrant DB     │    │   MongoDB       │
│                 │    │                 │    │                 │
│ ┌─────────────┐ │    │ ┌─────────────┐ │    │ ┌─────────────┐ │
│ │ Multi-Index │ │◄──►│ │ PDF Docs    │ │    │ │ Documents   │ │
│ │ Vector Store│ │    │ │ DOCX Docs   │ │    │ │ Queries     │ │
│ └─────────────┘ │    │ │ XLSX Docs   │ │    │ │ Metadata    │ │
│                 │    │ │ CSV Docs    │ │    │ └─────────────┘ │
│ ┌─────────────┐ │    │ │ TXT Docs    │ │    │                 │
│ │ LLM Service │ │    │ │ Image Docs  │ │    │ ┌─────────────┐ │
│ └─────────────┘ │    │ └─────────────┘ │    │ │ Redis Cache │ │
└─────────────────┘    └─────────────────┘    │ └─────────────┘ │
                                              └─────────────────┘
```

## Multi-Index Benefits

- **Type-Specific Collections**: Each document type gets its own Qdrant collection for optimized storage
- **Federated Search**: Queries search across all collections and merge results by relevance
- **Better Performance**: Smaller, focused collections for faster searches
- **Scalability**: Easy to add new document types and collections
- **Flexible Filtering**: Search specific file types or collections as needed

## Quick Start

### Prerequisites

- Docker and Docker Compose
- Python 3.8+ (for local development)
- Google Gemini API key (recommended) or OpenAI API key

### 1. Clone and Setup

```bash
git clone <repository-url>
cd rag_server
```

### 2. Environment Configuration

Create `.env` file:

```env
# LLM Configuration (Google Gemini recommended)
GOOGLE_API_KEY=your_gemini_api_key_here
OPENAI_API_KEY=your_openai_api_key_here  # Fallback

# Qdrant Configuration
QDRANT_URL=http://localhost:6333

# MongoDB Configuration
MONGODB_URL=mongodb://localhost:27017

# Redis Configuration
REDIS_URL=redis://localhost:6379

# App Configuration
UPLOAD_DIR=./uploads
CHUNK_SIZE=1000
CHUNK_OVERLAP=200
TOP_K=5
EMBEDDING_MODEL=all-MiniLM-L6-v2
```

### 3. Start Services

```bash
# Using Docker Compose (recommended)
docker-compose up -d

# Or using startup scripts
./start.sh  # Linux/Mac
start.bat   # Windows
```

### 4. Verify Installation

```bash
# Check health
curl http://localhost:8000/health

# Check detailed health
curl http://localhost:8000/health/detailed
```

## API Usage

### Upload Documents

```bash
# Upload a PDF
curl -X POST "http://localhost:8000/api/v1/documents/upload" \
  -H "Content-Type: multipart/form-data" \
  -F "file=@document.pdf" \
  -F "user_id=user123"

# Upload multiple files
curl -X POST "http://localhost:8000/api/v1/documents/upload" \
  -F "file=@report.docx" \
  -F "file=@data.xlsx" \
  -F "file=@image.png"
```

### Ask Questions

```bash
# Basic query (searches all collections)
curl -X POST "http://localhost:8000/api/v1/queries/ask" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "What are the main findings in the documents?",
    "user_id": "user123"
  }'

# Search specific file types
curl -X POST "http://localhost:8000/api/v1/queries/ask" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "What data is in the spreadsheets?",
    "search_mode": "file_type",
    "filter_metadata": {"file_type": "xlsx"}
  }'

# Search specific collection
curl -X POST "http://localhost:8000/api/v1/queries/ask" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "What is in the PDF documents?",
    "search_mode": "collection",
    "filter_metadata": {"collection": "rag_pdf_documents"}
  }'
```

### List Documents

```bash
# List all documents
curl "http://localhost:8000/api/v1/documents/"

# List user documents
curl "http://localhost:8000/api/v1/documents/?user_id=user123"

# Get document chunks
curl "http://localhost:8000/api/v1/documents/{file_id}/chunks"
```

### Health and Metrics

```bash
# Basic health check
curl "http://localhost:8000/health"

# Detailed health check
curl "http://localhost:8000/health/detailed"

# System metrics
curl "http://localhost:8000/health/metrics"

# LLM service info
curl "http://localhost:8000/health/llm/info"
```

## Multi-Index Search Modes

### 1. All Collections (`search_mode: "all"`)
- Searches across all document type collections
- Merges results by relevance score
- Best for general questions about all documents

### 2. File Type Search (`search_mode: "file_type"`)
- Searches only specific file type collections
- Use `filter_metadata: {"file_type": "pdf"}` for PDFs only
- Good for questions about specific document types

### 3. Collection Search (`search_mode: "collection"`)
- Searches specific Qdrant collections
- Use `filter_metadata: {"collection": "rag_pdf_documents"}`
- Most granular control over search scope

## Document Types and Collections

| File Type | Collection Name | Description |
|-----------|----------------|-------------|
| PDF | `rag_pdf_documents` | PDF documents with text extraction |
| DOCX | `rag_docx_documents` | Word documents |
| XLSX | `rag_xlsx_documents` | Excel spreadsheets |
| CSV | `rag_csv_documents` | CSV data files |
| TXT | `rag_txt_documents` | Plain text files |
| Images | `rag_image_documents` | PNG, JPG, JPEG with OCR |
| Default | `rag_documents` | Fallback for unknown types |

## Development

### Local Development Setup

```bash
# Install dependencies
pip install -r requirements.txt

# Start services manually
docker-compose up -d mongodb redis qdrant

# Run the application
python main.py
```

### Testing

```bash
# Run the test script
python test_rag_server.py

# Or test manually
curl -X POST "http://localhost:8000/api/v1/documents/upload" \
  -F "file=@test_document.pdf"

curl -X POST "http://localhost:8000/api/v1/queries/ask" \
  -H "Content-Type: application/json" \
  -d '{"query": "What is this document about?"}'
```

## Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `GOOGLE_API_KEY` | - | Google Gemini API key |
| `OPENAI_API_KEY` | - | OpenAI API key (fallback) |
| `QDRANT_URL` | `http://localhost:6333` | Qdrant server URL |
| `MONGODB_URL` | `mongodb://localhost:27017` | MongoDB connection URL |
| `REDIS_URL` | `redis://localhost:6379` | Redis connection URL |
| `UPLOAD_DIR` | `./uploads` | File upload directory |
| `CHUNK_SIZE` | `1000` | Text chunk size for embeddings |
| `CHUNK_OVERLAP` | `200` | Overlap between chunks |
| `TOP_K` | `5` | Number of results to return |
| `EMBEDDING_MODEL` | `all-MiniLM-L6-v2` | Sentence transformer model |

### LLM Priority Order

1. **Google Gemini** (primary) - Most cost-effective and powerful
2. **OpenAI GPT** (fallback) - Reliable alternative
3. **Ollama** (local) - Offline capability

## Monitoring

### Health Endpoints

- `/health` - Basic health check
- `/health/detailed` - Detailed service health
- `/health/metrics` - System metrics
- `/health/ready` - Kubernetes readiness probe

### Metrics

- Document upload counts by type
- Query processing statistics
- Vector store collection metrics
- LLM service performance

## Troubleshooting

### Common Issues

1. **Qdrant Connection Error**
   ```bash
   # Check if Qdrant is running
   docker-compose ps qdrant
   
   # Restart Qdrant
   docker-compose restart qdrant
   ```

2. **LLM API Errors**
   ```bash
   # Check API keys
   curl "http://localhost:8000/health/llm/info"
   
   # Verify environment variables
   echo $GOOGLE_API_KEY
   ```

3. **Document Processing Failures**
   ```bash
   # Check document status
   curl "http://localhost:8000/api/v1/documents/{file_id}"
   
   # View logs
   docker-compose logs rag-server
   ```

### Performance Optimization

- Adjust `CHUNK_SIZE` and `CHUNK_OVERLAP` for your documents
- Use `search_mode` to limit search scope
- Monitor collection sizes in Qdrant
- Consider using Redis for caching frequent queries

## License

MIT License - see LICENSE file for details.

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

## Support

For issues and questions:
- Check the troubleshooting section
- Review the health endpoints
- Check the logs: `docker-compose logs rag-server` 