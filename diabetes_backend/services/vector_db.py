import os
import json
import numpy as np
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
from typing import List, Dict, Tuple
import logging
from diabetes_backend.utils.pubmed_utils import search_pubmed

# Set up logger
logger = logging.getLogger(__name__)

class VectorDB:
    def __init__(self, model_name='all-MiniLM-L6-v2'):
        self.model = SentenceTransformer(model_name)
        self.articles = []
        self.embeddings = None
        self.index_file = "pubmed_index.json"

    def load_index(self):
        """Load articles and embeddings from index file if exists"""
        if os.path.exists(self.index_file):
            try:
                with open(self.index_file, 'r') as f:
                    data = json.load(f)
                    self.articles = data['articles']
                    
                    # Convert loaded embeddings to numpy array
                    if data['embeddings']:
                        self.embeddings = np.array(data['embeddings'])
                    else:
                        self.embeddings = None
                        
                    logger.info(f"Loaded {len(self.articles)} articles from index")
            except Exception as e:
                logger.error(f"Error loading index: {e}")
                self.articles = []
                self.embeddings = None

    def save_index(self):
        """Save articles and embeddings to index file"""
        try:
            data = {
                'articles': self.articles,
                'embeddings': self.embeddings.tolist() if self.embeddings is not None else []
            }
            with open(self.index_file, 'w') as f:
                json.dump(data, f)
            logger.info(f"Saved {len(self.articles)} articles to index")
        except Exception as e:
            logger.error(f"Error saving index: {e}")

    def update_index(self, query: str, max_results: int = 10):
        """Search PubMed and update index with new articles"""
        new_articles = search_pubmed(query, max_results)
        
        # Filter out existing articles by PMID
        existing_pmids = {a['pmid'] for a in self.articles}
        unique_articles = [a for a in new_articles if a['pmid'] not in existing_pmids]
        
        if not unique_articles:
            logger.info("No new articles found to add to index")
            return
        
        # Generate embeddings for new articles
        texts = [f"{a['title']}\n{a['abstract']}" for a in unique_articles]
        new_embeddings = self.model.encode(texts, show_progress_bar=False)
        
        # Convert to numpy array if needed
        if not isinstance(new_embeddings, np.ndarray):
            new_embeddings = np.array(new_embeddings)
        
        # Update index
        self.articles.extend(unique_articles)
        if self.embeddings is None:
            self.embeddings = new_embeddings
        else:
            # Ensure existing embeddings are numpy array
            if not isinstance(self.embeddings, np.ndarray):
                self.embeddings = np.array(self.embeddings)
                
            self.embeddings = np.vstack([self.embeddings, new_embeddings])
        
        logger.info(f"Added {len(unique_articles)} new articles to index")
        self.save_index()

    def retrieve_relevant_articles(self, query: str, top_k: int = 3) -> List[Dict]:
        """Retrieve top-k most relevant articles for a query"""
        if not self.articles or self.embeddings is None:
            logger.warning("No articles in index, performing fresh search")
            self.update_index(query, max_results=top_k)
            if not self.articles:
                return []
        
        # Embed the query
        query_embedding = self.model.encode([query])
        
        # Ensure embeddings are numpy arrays
        if not isinstance(query_embedding, np.ndarray):
            query_embedding = np.array(query_embedding)
        if not isinstance(self.embeddings, np.ndarray):
            self.embeddings = np.array(self.embeddings)
        
        # Calculate cosine similarity
        similarities = cosine_similarity(query_embedding, self.embeddings)[0]
        
        # Get top-k indices
        top_indices = similarities.argsort()[-top_k:][::-1]
        
        # Return article details with similarity scores
        results = []
        for idx in top_indices:
            article = self.articles[idx]
            article['similarity'] = float(similarities[idx])
            results.append(article)
        
        return results