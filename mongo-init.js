// MongoDB initialization script
db = db.getSiblingDB('rag_db');

// Create collections
db.createCollection('documents');
db.createCollection('embeddings');
db.createCollection('sessions');
db.createCollection('queries');

// Create indexes for better performance
db.documents.createIndex({ "file_id": 1 }, { unique: true });
db.documents.createIndex({ "upload_date": -1 });
db.documents.createIndex({ "file_type": 1 });
db.documents.createIndex({ "user_id": 1 });

db.embeddings.createIndex({ "document_id": 1 });
db.embeddings.createIndex({ "chunk_id": 1 }, { unique: true });

db.sessions.createIndex({ "session_id": 1 }, { unique: true });
db.sessions.createIndex({ "created_at": -1 });

db.queries.createIndex({ "session_id": 1 });
db.queries.createIndex({ "timestamp": -1 });

// Insert initial configuration
db.config.insertOne({
    "key": "system_config",
    "max_file_size": 50 * 1024 * 1024, // 50MB
    "supported_formats": ["pdf", "docx", "xlsx", "csv", "txt", "png", "jpg", "jpeg"],
    "chunk_size": 1000,
    "chunk_overlap": 200,
    "embedding_model": "all-MiniLM-L6-v2",
    "llm_provider": "ollama",
    "created_at": new Date()
});

print("MongoDB initialization completed successfully!"); 