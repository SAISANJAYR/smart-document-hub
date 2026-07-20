import os
import chromadb
from chromadb.config import Settings
import logging
from typing import List, Dict, Any

# We use langchain's text splitter to chunk documents intelligently
from langchain_text_splitters import RecursiveCharacterTextSplitter

logger = logging.getLogger(__name__)

class VectorDBService:
    def __init__(self):
        # Initialize a persistent local ChromaDB client
        # The database will be stored in backend/chroma_data/
        db_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "chroma_data")
        
        try:
            self.client = chromadb.PersistentClient(path=db_path)
            
            # Get or create the collection for storing our document vectors
            # ChromaDB uses sentence-transformers default (all-MiniLM-L6-v2) automatically if installed!
            self.collection = self.client.get_or_create_collection(
                name="document_chunks",
                metadata={"hnsw:space": "cosine"} # Use cosine similarity for better semantic search
            )
            logger.info("Successfully connected to local ChromaDB.")
        except Exception as e:
            logger.error(f"Failed to initialize ChromaDB: {e}")
            self.client = None
            self.collection = None

    def add_document(self, document_id: str, text: str, metadata: Dict[str, Any] = None):
        """
        Takes raw text, chunks it, and saves the vectors to ChromaDB.
        """
        if not self.collection:
            logger.error("ChromaDB not initialized, skipping vector ingestion.")
            return

        # 1. Chunk the text
        # We split text into chunks of 1000 characters, with 200 characters overlap
        # Overlap ensures we don't accidentally cut a sentence or context in half.
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=200,
            length_function=len,
        )
        
        chunks = text_splitter.split_text(text)
        
        if not chunks:
            logger.warning(f"No text chunks generated for document {document_id}")
            return

        # 2. Prepare data for ChromaDB
        documents = []
        metadatas = []
        ids = []
        
        for i, chunk in enumerate(chunks):
            documents.append(chunk)
            
            # Combine provided metadata with chunk-specific metadata
            chunk_meta = metadata.copy() if metadata else {}
            chunk_meta["document_id"] = document_id
            chunk_meta["chunk_index"] = i
            metadatas.append(chunk_meta)
            
            # Create a unique ID for this chunk
            ids.append(f"{document_id}_chunk_{i}")

        # 3. Insert into ChromaDB
        # ChromaDB automatically handles embedding the `documents` list locally!
        try:
            self.collection.add(
                documents=documents,
                metadatas=metadatas,
                ids=ids
            )
            logger.info(f"Successfully added {len(chunks)} chunks to Vector DB for document {document_id}")
        except Exception as e:
            logger.error(f"Failed to insert chunks into ChromaDB: {e}")

    def search(self, query: str, n_results: int = 5) -> List[Dict[str, Any]]:
        """
        Search for the most relevant document chunks based on a text query.
        """
        if not self.collection:
            return []
            
        try:
            # Query ChromaDB (it automatically embeds the query and performs ANN search)
            results = self.collection.query(
                query_texts=[query],
                n_results=n_results
            )
            
            # Format the results into a clean list of dictionaries
            formatted_results = []
            if results["documents"] and len(results["documents"]) > 0:
                for i in range(len(results["documents"][0])):
                    formatted_results.append({
                        "text": results["documents"][0][i],
                        "metadata": results["metadatas"][0][i],
                        "distance": results["distances"][0][i] if "distances" in results and results["distances"] else None
                    })
                    
            return formatted_results
            
        except Exception as e:
            logger.error(f"Semantic search failed: {e}")
            return []

# Singleton instance
vector_db_service = VectorDBService()
