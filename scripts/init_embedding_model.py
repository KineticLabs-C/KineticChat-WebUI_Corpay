#!/usr/bin/env python3
"""
Initialize and verify the embedding model for the demo environment.
This script ensures the all-MiniLM-L6-v2 model is downloaded and working correctly.
"""

import os
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from sentence_transformers import SentenceTransformer
from qdrant_client import QdrantClient
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def verify_embedding_model():
    """Download and verify the embedding model."""
    print("=" * 60)
    print("KineticChat WebUI Demo - Embedding Model Initialization")
    print("=" * 60)
    
    # Get configuration from environment
    model_name = os.getenv("EMBEDDING_MODEL", "all-MiniLM-L6-v2")
    expected_dim = int(os.getenv("EMBEDDING_DIMENSION", "384"))
    
    print(f"\nInitializing model: {model_name}")
    print(f"Expected dimensions: {expected_dim}")
    
    try:
        # Load the model (will download if not cached)
        print("\nLoading model (may download if not cached)...")
        model = SentenceTransformer(model_name)
        
        # Test embedding generation
        test_text = "What pharmacy services are available?"
        print(f"\nTesting with: '{test_text}'")
        
        embedding = model.encode(test_text)
        actual_dim = len(embedding)
        
        print(f"Generated embedding with {actual_dim} dimensions")
        
        # Verify dimensions match
        if actual_dim == expected_dim:
            print(f"[SUCCESS] Dimensions match expected: {expected_dim}")
        else:
            print(f"[ERROR] Dimension mismatch!")
            print(f"  Expected: {expected_dim}")
            print(f"  Actual: {actual_dim}")
            return False
            
        # Show model info
        print(f"\nModel Information:")
        print(f"  Max sequence length: {model.max_seq_length}")
        print(f"  Model size: ~80MB (vs ~420MB for all-mpnet-base-v2)")
        print(f"  Speed: ~3x faster than all-mpnet-base-v2")
        
        return True
        
    except Exception as e:
        print(f"\n[ERROR] Loading model: {e}")
        return False

def verify_qdrant_connection():
    """Verify connection to Qdrant and collection."""
    print("\n" + "=" * 60)
    print("Verifying Qdrant Connection")
    print("=" * 60)
    
    qdrant_url = os.getenv("QDRANT_URL")
    qdrant_key = os.getenv("QDRANT_API_KEY")
    collection_name = os.getenv("QDRANT_COLLECTION_NAME", "kinetic_corpay_finance_rag")
    
    if not qdrant_url or not qdrant_key:
        print("[ERROR] Qdrant credentials not found in environment")
        return False
    
    try:
        # Connect to Qdrant
        print(f"\nConnecting to Qdrant...")
        client = QdrantClient(url=qdrant_url, api_key=qdrant_key)
        
        # Get collection info
        print(f"Checking collection: {collection_name}")
        info = client.get_collection(collection_name)
        
        print(f"\n[SUCCESS] Collection found!")
        print(f"  Points count: {info.points_count}")
        print(f"  Vector size: {info.config.params.vectors.size}")
        print(f"  Distance: {info.config.params.vectors.distance}")
        
        # Verify vector dimensions match
        expected_dim = int(os.getenv("EMBEDDING_DIMENSION", "384"))
        if info.config.params.vectors.size == expected_dim:
            print(f"[SUCCESS] Vector dimensions match: {expected_dim}")
        else:
            print(f"[WARNING] Dimension mismatch!")
            print(f"  Collection has: {info.config.params.vectors.size}")
            print(f"  Model expects: {expected_dim}")
            return False
            
        return True
        
    except Exception as e:
        print(f"\n[ERROR] Connecting to Qdrant: {e}")
        return False

def test_search():
    """Test a sample search with the configured model and collection."""
    print("\n" + "=" * 60)
    print("Testing Search Functionality")
    print("=" * 60)
    
    try:
        # Load model and connect to Qdrant
        model_name = os.getenv("EMBEDDING_MODEL", "all-MiniLM-L6-v2")
        collection_name = os.getenv("QDRANT_COLLECTION_NAME", "kinetic_corpay_finance_rag")
        
        print(f"\nLoading model: {model_name}")
        model = SentenceTransformer(model_name)
        
        print("Connecting to Qdrant...")
        client = QdrantClient(
            url=os.getenv("QDRANT_URL"),
            api_key=os.getenv("QDRANT_API_KEY")
        )
        
        # Test query
        test_query = "What health screenings are available?"
        print(f"\nTest query: '{test_query}'")
        
        # Generate embedding
        print("Generating query embedding...")
        query_embedding = model.encode(test_query).tolist()
        
        # Search
        print(f"Searching in collection: {collection_name}")
        results = client.search(
            collection_name=collection_name,
            query_vector=query_embedding,
            limit=3
        )
        
        print(f"\n[SUCCESS] Search successful! Found {len(results)} results")
        
        # Display results
        for i, result in enumerate(results, 1):
            text = result.payload.get('text', '')[:100]
            score = result.score
            print(f"\n  Result {i} (score: {score:.3f}):")
            print(f"    {text}...")
            
        return True
        
    except Exception as e:
        print(f"\n[ERROR] During search test: {e}")
        return False

def main():
    """Run all verification steps."""
    success = True
    
    # Step 1: Verify embedding model
    if not verify_embedding_model():
        success = False
        
    # Step 2: Verify Qdrant connection
    if not verify_qdrant_connection():
        success = False
        
    # Step 3: Test search
    if not test_search():
        success = False
    
    # Summary
    print("\n" + "=" * 60)
    if success:
        print("[SUCCESS] ALL CHECKS PASSED - Demo environment is ready!")
        print("\nYou can now run the demo server with:")
        print("  cd KineticChat_WebUI_Demo")
        print("  uvicorn app.main:app --reload --port 8000")
    else:
        print("[FAILURE] SOME CHECKS FAILED - Please review the errors above")
        print("\nCommon issues:")
        print("  1. Model not downloaded - will auto-download on first run")
        print("  2. Qdrant credentials incorrect - check .env file")
        print("  3. Collection doesn't exist - run KineticData_RAG pipeline first")
        print("  4. Dimension mismatch - ensure collection uses 384-dim vectors")
    
    print("=" * 60)
    
    return 0 if success else 1

if __name__ == "__main__":
    exit(main())