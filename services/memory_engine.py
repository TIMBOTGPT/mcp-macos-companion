#!/usr/bin/env python3
"""
MCP macOS Companion - Memory Engine
Persistent memory with embeddings for intelligent recall
"""

import sqlite3
import json
import logging
import threading
import time
import numpy as np
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass
import requests
from sentence_transformers import SentenceTransformer
import faiss
from flask import Flask, request, jsonify
from flask_cors import CORS

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class MemoryEntry:
    """A single memory entry with embeddings"""
    id: str
    content: str
    category: str
    timestamp: float
    metadata: Dict[str, Any]
    embedding: Optional[np.ndarray] = None
    tags: List[str] = None
    
    def __post_init__(self):
        if self.tags is None:
            self.tags = []

class MemoryEngine:
    """Intelligent memory system with embeddings and semantic search"""
    
    def __init__(self, db_path: str = "/Users/mark/.mcp/memory.db", port: int = 8081):
        self.db_path = db_path
        self.port = port
        self.app = Flask(__name__)
        CORS(self.app)
        
        # Initialize sentence transformer for embeddings
        self.model = SentenceTransformer('all-MiniLM-L6-v2')
        self.embedding_dim = 384  # Dimension of all-MiniLM-L6-v2
        
        # Initialize FAISS index for vector search
        self.index = faiss.IndexFlatIP(self.embedding_dim)  # Inner product for cosine similarity
        self.id_to_index: Dict[str, int] = {}  # Map memory IDs to FAISS indices
        
        # Database connection with thread safety
        self.db_lock = threading.Lock()
        
        # Initialize database and FAISS index
        self._init_database()
        self._load_existing_embeddings()
        
        # Setup Flask routes
        self._setup_routes()
        
        # Service registration
        self._register_with_service_registry()
    
    def _init_database(self):
        """Initialize SQLite database"""
        import os
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        
        with sqlite3.connect(self.db_path) as conn:
            conn.execute('''
                CREATE TABLE IF NOT EXISTS memories (
                    id TEXT PRIMARY KEY,
                    content TEXT NOT NULL,
                    category TEXT NOT NULL,
                    timestamp REAL NOT NULL,
                    metadata TEXT NOT NULL,
                    tags TEXT NOT NULL,
                    embedding BLOB
                )
            ''')
            
            conn.execute('''
                CREATE INDEX IF NOT EXISTS idx_category ON memories(category)
            ''')
            
            conn.execute('''
                CREATE INDEX IF NOT EXISTS idx_timestamp ON memories(timestamp)
            ''')
            
            conn.execute('''
                CREATE VIRTUAL TABLE IF NOT EXISTS memories_fts USING fts5(
                    id, content, category, tags
                )
            ''')
    
    def _load_existing_embeddings(self):
        """Load existing embeddings into FAISS index"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute('SELECT id, embedding FROM memories WHERE embedding IS NOT NULL')
            
            for row in cursor:
                memory_id, embedding_blob = row
                if embedding_blob:
                    embedding = np.frombuffer(embedding_blob, dtype=np.float32)
                    # Normalize for cosine similarity
                    embedding = embedding / np.linalg.norm(embedding)
                    
                    index_pos = self.index.ntotal
                    self.index.add(embedding.reshape(1, -1))
                    self.id_to_index[memory_id] = index_pos
    
    def _setup_routes(self):
        """Setup Flask API routes"""
        
        @self.app.route('/store', methods=['POST'])
        def store_memory():
            data = request.json
            memory_id = data.get('id', f"mem_{int(time.time() * 1000)}")
            
            # Create embedding
            content = data['content']
            embedding = self.model.encode([content])[0]
            embedding = embedding / np.linalg.norm(embedding)  # Normalize
            
            # Store in database
            entry = MemoryEntry(
                id=memory_id,
                content=content,
                category=data.get('category', 'general'),
                timestamp=data.get('timestamp', time.time()),
                metadata=data.get('metadata', {}),
                tags=data.get('tags', [])
            )
            
            with self.db_lock:
                with sqlite3.connect(self.db_path) as conn:
                    conn.execute('''
                        INSERT OR REPLACE INTO memories 
                        (id, content, category, timestamp, metadata, tags, embedding)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        entry.id,
                        entry.content,
                        entry.category,
                        entry.timestamp,
                        json.dumps(entry.metadata),
                        json.dumps(entry.tags),
                        embedding.tobytes()
                    ))
                    
                    # Update FTS index
                    conn.execute('''
                        INSERT OR REPLACE INTO memories_fts 
                        (id, content, category, tags)
                        VALUES (?, ?, ?, ?)
                    ''', (
                        entry.id,
                        entry.content,
                        entry.category,
                        ' '.join(entry.tags)
                    ))
                
                # Add to FAISS index
                if memory_id in self.id_to_index:
                    # Remove old entry and rebuild index (FAISS doesn't support updates)
                    self._rebuild_faiss_index()
                
                index_pos = self.index.ntotal
                self.index.add(embedding.reshape(1, -1))
                self.id_to_index[memory_id] = index_pos
            
            return jsonify({'status': 'stored', 'id': memory_id})
        
        @self.app.route('/search', methods=['POST'])
        def search_memories():
            data = request.json
            query = data['query']
            limit = data.get('limit', 10)
            category_filter = data.get('category')
            time_range = data.get('time_range')  # In hours
            
            # Get embedding for query
            query_embedding = self.model.encode([query])[0]
            query_embedding = query_embedding / np.linalg.norm(query_embedding)
            
            # Search in FAISS
            if self.index.ntotal > 0:
                scores, indices = self.index.search(query_embedding.reshape(1, -1), 
                                                  min(limit * 2, self.index.ntotal))
                
                # Get memory IDs from indices
                candidate_ids = []
                for i, idx in enumerate(indices[0]):
                    if idx != -1:  # Valid result
                        for mem_id, mem_idx in self.id_to_index.items():
                            if mem_idx == idx:
                                candidate_ids.append((mem_id, scores[0][i]))
                                break
            else:
                candidate_ids = []
            
            # Fetch full memory entries and apply filters
            results = []
            with sqlite3.connect(self.db_path) as conn:
                for memory_id, score in candidate_ids:
                    cursor = conn.execute('''
                        SELECT content, category, timestamp, metadata, tags
                        FROM memories WHERE id = ?
                    ''', (memory_id,))
                    
                    row = cursor.fetchone()
                    if row:
                        content, category, timestamp, metadata_json, tags_json = row
                        
                        # Apply filters
                        if category_filter and category != category_filter:
                            continue
                        
                        if time_range:
                            cutoff_time = time.time() - (time_range * 3600)
                            if timestamp < cutoff_time:
                                continue
                        
                        results.append({
                            'id': memory_id,
                            'content': content,
                            'category': category,
                            'timestamp': timestamp,
                            'metadata': json.loads(metadata_json),
                            'tags': json.loads(tags_json),
                            'similarity_score': float(score)
                        })
                        
                        if len(results) >= limit:
                            break
            
            return jsonify({'results': results})
        
        @self.app.route('/search', methods=['GET'])
        def search_interface():
            """Serve the memory search interface"""
            try:
                interface_path = "/Users/mark/Desktop/MCP STUFF/mcp-macos-companion/services/memory_interface.html"
                with open(interface_path, 'r') as f:
                    return f.read(), 200, {'Content-Type': 'text/html'}
            except FileNotFoundError:
                return '''
                <!DOCTYPE html>
                <html>
                <head><title>Memory Interface</title></head>
                <body>
                    <h1>Memory Search Interface</h1>
                    <p>Use POST requests to /search with JSON data:</p>
                    <pre>
                    POST /search
                    Content-Type: application/json
                    
                    {
                        "query": "your search query",
                        "limit": 10,
                        "category": "optional category filter"
                    }
                    </pre>
                    <p>Available endpoints:</p>
                    <ul>
                        <li>POST /search - Semantic search</li>
                        <li>POST /text_search - Text search</li>
                        <li>POST /store - Store memory</li>
                        <li>GET /stats - Get statistics</li>
                        <li>GET /categories - Get categories</li>
                        <li>GET /health - Health check</li>
                    </ul>
                </body>
                </html>
                ''', 200, {'Content-Type': 'text/html'}
        
        @self.app.route('/text_search', methods=['POST'])
        def text_search():
            """Full-text search using SQLite FTS"""
            data = request.json
            query = data['query']
            limit = data.get('limit', 10)
            
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute('''
                    SELECT m.id, m.content, m.category, m.timestamp, m.metadata, m.tags
                    FROM memories_fts fts
                    JOIN memories m ON fts.id = m.id
                    WHERE memories_fts MATCH ?
                    ORDER BY rank
                    LIMIT ?
                ''', (query, limit))
                
                results = []
                for row in cursor:
                    memory_id, content, category, timestamp, metadata_json, tags_json = row
                    results.append({
                        'id': memory_id,
                        'content': content,
                        'category': category,
                        'timestamp': timestamp,
                        'metadata': json.loads(metadata_json),
                        'tags': json.loads(tags_json)
                    })
            
            return jsonify({'results': results})
        
        @self.app.route('/categories', methods=['GET'])
        def get_categories():
            """Get all unique categories"""
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute('SELECT DISTINCT category FROM memories')
                categories = [row[0] for row in cursor]
            
            return jsonify({'categories': categories})
        
        @self.app.route('/stats', methods=['GET'])
        def get_stats():
            """Get memory statistics"""
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute('SELECT COUNT(*) FROM memories')
                total_memories = cursor.fetchone()[0]
                
                cursor = conn.execute('''
                    SELECT category, COUNT(*) 
                    FROM memories 
                    GROUP BY category
                ''')
                category_counts = dict(cursor.fetchall())
            
            return jsonify({
                'total_memories': total_memories,
                'category_counts': category_counts,
                'faiss_index_size': self.index.ntotal
            })
        
        @self.app.route('/health', methods=['GET'])
        def health():
            return jsonify({
                'status': 'healthy',
                'timestamp': time.time(),
                'total_memories': self.index.ntotal
            })
    
    def _rebuild_faiss_index(self):
        """Rebuild FAISS index from database"""
        self.index = faiss.IndexFlatIP(self.embedding_dim)
        self.id_to_index.clear()
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute('SELECT id, embedding FROM memories WHERE embedding IS NOT NULL')
            
            for row in cursor:
                memory_id, embedding_blob = row
                if embedding_blob:
                    embedding = np.frombuffer(embedding_blob, dtype=np.float32)
                    embedding = embedding / np.linalg.norm(embedding)
                    
                    index_pos = self.index.ntotal
                    self.index.add(embedding.reshape(1, -1))
                    self.id_to_index[memory_id] = index_pos
    
    def _register_with_service_registry(self):
        """Register this service with the service registry"""
        try:
            registration_data = {
                'name': 'memory_engine',
                'host': 'localhost',
                'port': self.port,
                'health_endpoint': '/health',
                'capabilities': ['memory_storage', 'semantic_search', 'text_search'],
                'metadata': {
                    'embedding_model': 'all-MiniLM-L6-v2',
                    'database_path': self.db_path
                }
            }
            
            response = requests.post('http://localhost:8080/register', 
                                   json=registration_data, timeout=10)
            
            if response.status_code == 200:
                logger.info("Successfully registered with service registry")
            else:
                logger.error(f"Failed to register with service registry: {response.text}")
        except Exception as e:
            logger.error(f"Could not register with service registry: {e}")
    
    def start(self):
        """Start the memory engine service"""
        logger.info(f"Starting Memory Engine on port {self.port}")
        self.app.run(host='0.0.0.0', port=self.port, debug=False, threaded=True)

if __name__ == "__main__":
    engine = MemoryEngine()
    try:
        engine.start()
    except KeyboardInterrupt:
        logger.info("Memory Engine stopped")
