import requests
import json
import re
import xml.etree.ElementTree as ET
from typing import List, Dict
import logging
from config.config import PUBMED_API_KEY, PUBMED_API_URL

# Set up logger
logger = logging.getLogger(__name__)

def search_pubmed(query: str, max_results: int = 5) -> List[Dict]:
    """
    Search PubMed for articles related to the query
    
    Args:
        query: Search query string
        max_results: Maximum number of results to return
        
    Returns:
        List of article dictionaries with keys: 
        ['pmid', 'title', 'abstract', 'authors', 'journal', 'pub_date', 'doi']
    """
    try:
        # Step 1: Search for article IDs
        params = {
            'db': 'pubmed',
            'term': query,
            'retmode': 'json',
            'retmax': max_results,
            'api_key': PUBMED_API_KEY
        }
        
        try:
            response = requests.get(
                f"{PUBMED_API_URL}/esearch.fcgi",
                params=params,
                timeout=30
            )
            response.raise_for_status()
            
            # Handle malformed JSON responses
            try:
                data = response.json()
            except json.JSONDecodeError:
                # Try to fix common malformation issues
                cleaned = response.text.strip()
                if cleaned.startswith('[') and cleaned.endswith(']'):
                    data = json.loads(cleaned)[0]
                else:
                    raise
        except Exception as e:
            logger.error(f"PubMed esearch API error: {str(e)}")
            return []
        
        id_list = data.get('esearchresult', {}).get('idlist', [])
        
        if not id_list:
            logger.info(f"No PubMed results found for query: {query}")
            return []
            
        logger.info(f"Found {len(id_list)} PubMed IDs for query: {query}")
        
        # Step 2: Fetch article details using XML format (CORRECTED)
        fetch_params = {
            'db': 'pubmed',
            'id': ','.join(id_list),
            'retmode': 'xml',  # CHANGED: Use XML instead of JSON
            'rettype': 'abstract',  # ADDED: Specify we want abstracts
            'api_key': PUBMED_API_KEY
        }
        
        try:
            fetch_response = requests.get(
                f"{PUBMED_API_URL}/efetch.fcgi",
                params=fetch_params,
                timeout=30
            )
            fetch_response.raise_for_status()
            
            # Parse XML response instead of JSON
            try:
                root = ET.fromstring(fetch_response.text)
                articles = []
                
                for article_elem in root.findall('.//PubmedArticle'):
                    try:
                        # Extract PMID
                        pmid_elem = article_elem.find('.//PMID')
                        pmid = pmid_elem.text if pmid_elem is not None and pmid_elem.text else ''
                        
                        # Extract Title
                        title_elem = article_elem.find('.//ArticleTitle')
                        title = title_elem.text if title_elem is not None and title_elem.text else ''
                        
                        # Extract Abstract
                        abstract_texts = []
                        for abstract_elem in article_elem.findall('.//AbstractText'):
                            if abstract_elem.text:
                                # Handle different abstract section labels
                                label = abstract_elem.get('Label', '')
                                text = abstract_elem.text
                                if label:
                                    abstract_texts.append(f"{label}: {text}")
                                else:
                                    abstract_texts.append(text)
                        abstract = ' '.join(abstract_texts)
                        
                        # Extract Authors
                        authors = []
                        for author_elem in article_elem.findall('.//Author'):
                            last_name_elem = author_elem.find('LastName')
                            first_name_elem = author_elem.find('ForeName')
                            if (last_name_elem is not None and last_name_elem.text and 
                                first_name_elem is not None and first_name_elem.text):
                                authors.append(f"{first_name_elem.text} {last_name_elem.text}")
                            elif last_name_elem is not None and last_name_elem.text:
                                authors.append(last_name_elem.text)
                        
                        # Extract Journal
                        journal_elem = article_elem.find('.//Journal/Title')
                        if journal_elem is None:
                            journal_elem = article_elem.find('.//Journal/ISOAbbreviation')
                        journal = journal_elem.text if journal_elem is not None and journal_elem.text else ''
                        
                        # Extract Publication Date
                        pub_date_year = article_elem.find('.//PubDate/Year')
                        pub_date_month = article_elem.find('.//PubDate/Month')
                        pub_date = ""
                        if pub_date_year is not None and pub_date_year.text:
                            pub_date = pub_date_year.text
                            if pub_date_month is not None and pub_date_month.text:
                                pub_date += f" {pub_date_month.text}"
                        
                        # Extract DOI
                        doi = ''
                        for id_elem in article_elem.findall('.//ArticleId'):
                            if id_elem.get('IdType') == 'doi' and id_elem.text:
                                doi = id_elem.text
                                break
                        
                        # Only add if we have essential information
                        if pmid and (title or abstract):
                            article = {
                                'pmid': pmid,
                                'title': title.strip() if title else '',
                                'abstract': abstract.strip() if abstract else '',
                                'authors': authors,
                                'journal': journal.strip() if journal else '',
                                'pub_date': pub_date.strip() if pub_date else '',
                                'doi': doi.strip() if doi else ''
                            }
                            articles.append(article)
                            logger.debug(f"Parsed article PMID: {pmid}, Title: {title[:50] if title else 'No title'}")
                            
                    except Exception as e:
                        logger.warning(f"Error parsing individual article: {e}")
                        continue
                        
                logger.info(f"Successfully parsed {len(articles)} articles from PubMed XML")
                return articles
                
            except ET.ParseError as e:
                logger.error(f"PubMed XML parsing error: {e}")
                logger.error(f"Response text preview: {fetch_response.text[:500]}")
                return []
                
        except Exception as e:
            logger.error(f"PubMed efetch API error: {str(e)}")
            return []
        
    except requests.exceptions.RequestException as e:
        logger.error(f"PubMed API network error: {e}")
        return []
    except Exception as e:
        logger.error(f"Error processing PubMed search: {e}")
        return []