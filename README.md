# RAG Server

A scalable, fault-tolerant Retrieval-Augmented Generation (RAG) server supporting PDFs, tables, and images, using local MongoDB via Docker.

## Features

- **Multi-format Document Support**: PDFs, Word documents, Excel spreadsheets, CSV files, text files, and images (PNG, JPG)
- **Multi-index Vector Storage**: Separate Qdrant collections for different document types with federated search
- **Local LLM Integration**: Google Gemini for text generation
- **Async Processing**: Background document processing with status tracking
- **Monitoring**: Prometheus metrics and health checks
- **Docker Support**: Complete containerized setup with Docker Compose
- **Offline Mode**: Development mode without external dependencies

## Architecture

- **FastAPI**: Modern async web framework
- **MongoDB**: Document metadata and user data storage
- **Redis**: Caching and session management
- **Qdrant**: Multi-collection vector database
- **Google Gemini**: LLM for text generation
- **Sentence Transformers**: Local embedding generation

## Quick Start

### Prerequisites

- Docker and Docker Compose
- Google Gemini API key (optional for offline mode)

### 1. Clone and Setup

```bash
git clone <repository-url>
cd rag_server
```

### 2. Environment Configuration

Create a `.env` file:

```env
# Required for LLM functionality
GEMINI_API_KEY=your_gemini_api_key_here

# Optional overrides
MONGODB_URI=mongodb://admin:password123@localhost:27018/rag_db?authSource=admin
REDIS_URL=redis://localhost:6379/0
QDRANT_URL=http://localhost:6333
```

### 3. Start Services

```bash
# Start all services
docker-compose up -d

# Or start individual services
docker-compose up -d mongodb redis qdrant
```

### 4. Run the Server

```bash
# Install dependencies
pip install -r requirements.txt

# Start the server
python main.py
```

The server will be available at `http://localhost:8000`

## API Documentation

Once running, visit:
- **Interactive API Docs**: `http://localhost:8000/docs`
- **Alternative API Docs**: `http://localhost:8000/redoc`

## Usage Examples

### Upload a Document

```bash
curl -X POST "http://localhost:8000/api/v1/documents/upload" \
  -H "accept: application/json" \
  -H "Content-Type: multipart/form-data" \
  -F "file=@your_document.pdf"
```

### Query Documents

```bash
curl -X POST "http://localhost:8000/api/v1/queries/ask" \
  -H "accept: application/json" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "What is the main topic of the document?",
    "top_k": 5
  }'
```

### Check Document Status

```bash
curl -X GET "http://localhost:8000/api/v1/documents/{file_id}/status"
```

## Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `GEMINI_API_KEY` | None | Google Gemini API key |
| `MONGODB_URI` | `mongodb://admin:password123@localhost:27018/rag_db?authSource=admin` | MongoDB connection string |
| `REDIS_URL` | `redis://localhost:6379/0` | Redis connection string |
| `QDRANT_URL` | `http://localhost:6333` | Qdrant vector database URL |
| `LLM_MODEL` | `gemini-pro` | LLM model name |
| `EMBEDDING_MODEL` | `all-MiniLM-L6-v2` | Sentence transformer model |
| `MAX_FILE_SIZE` | `52428800` | Maximum file size (50MB) |
| `CHUNK_SIZE` | `1000` | Text chunk size |
| `CHUNK_OVERLAP` | `200` | Chunk overlap |
| `TOP_K` | `5` | Number of results to return |

### Offline Mode

For development without external services:

```bash
# Set offline mode
export OFFLINE_MODE=true

# Start server (will work without MongoDB, Redis, Qdrant)
python main.py
```

## API Endpoints

### Documents
- `POST /api/v1/documents/upload` - Upload document
- `GET /api/v1/documents/` - List documents
- `GET /api/v1/documents/{file_id}` - Get document info
- `DELETE /api/v1/documents/{file_id}` - Delete document
- `GET /api/v1/documents/{file_id}/chunks` - Get document chunks
- `GET /api/v1/documents/{file_id}/status` - Get processing status

### Queries
- `POST /api/v1/queries/ask` - Ask question about documents
- `POST /api/v1/queries/search` - Search documents
- `GET /api/v1/queries/history` - Get query history

### Health & Monitoring
- `GET /health` - Health check
- `GET /metrics` - Prometheus metrics
- `GET /api/v1/health/services` - Service health status

## Development

### Project Structure

```
rag_server/
├── app/
│   ├── api/           # API routes
│   ├── core/          # Configuration and core services
│   └── services/      # Business logic services
├── docker-compose.yml # Docker services
├── main.py           # Application entry point
└── requirements.txt  # Python dependencies
```

### Running Tests

```bash
# Run tests
python -m pytest

# Run with coverage
python -m pytest --cov=app
```

### Adding New Document Types

1. Update `supported_formats` in `app/core/config.py`
2. Add processing logic in `app/services/document_processor.py`
3. Update collection mapping in `app/services/multi_index_vector_store.py`

## Monitoring

### Prometheus Metrics

The server exposes metrics at `/metrics`:
- Document upload counts
- Query response times
- Vector store operations
- LLM API calls

### Health Checks

- `GET /health` - Basic health check
- `GET /api/v1/health/services` - Detailed service status

## Troubleshooting

### Common Issues

1. **Port Conflicts**: Change ports in `docker-compose.yml`
2. **Memory Issues**: Increase Docker memory limits
3. **API Key Issues**: Verify Gemini API key is set correctly
4. **Service Unavailable**: Check Docker containers are running

### Logs

```bash
# View application logs
tail -f logs/rag_server.log

# View Docker logs
docker-compose logs -f
```

## License

MIT License 