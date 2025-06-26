"""
PGS Catalog Integration for Existing DMP Platform
==============================================

Plugs into your existing DMP infrastructure:
- Uses your existing OCR system
- Uses your existing DeepSeek integration  
- Uses your existing MongoDB
- Simply adds PGS Catalog functionality

What this adds:
1. PGS Catalog API client with rate limiting
2. Genetic data parser that works with your OCR output
3. Simple genetics Q&A for doctors
4. One main function: answer_genetic_question()

Dependencies needed:
pip install requests aiohttp

No new environment variables needed - uses your existing DEEPSEEK_API_KEY
"""

import asyncio
import logging
import time
import json
import re
from datetime import datetime
from typing import Awaitable, Callable, Dict, List, Optional, Any
from dataclasses import dataclass, asdict
import hashlib

# HTTP client for PGS API
import requests
import aiohttp

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class SimpleGeneticResult:
    """Simple result for doctors"""
    condition: str
    risk_level: str  # ΧΑΜΗΛΟΣ, ΜΕΤΡΙΟΣ, ΥΨΗΛΟΣ, ΠΟΛΥ ΥΨΗΛΟΣ
    percentile: int  # 0-100
    confidence: str  # Υψηλή, Μέτρια, Χαμηλή
    recommendations: List[str]
    explanation: str
    emoji: str  # 🟢🟡🔴
    pgs_scores_used: Optional[List[str]] = None


class PGSCatalogClient:
    """Enhanced PGS Catalog API client with full endpoint support"""
    
    BASE_URL = "https://www.pgscatalog.org/rest/"
    RATE_LIMIT = 100  # per minute
    PAGE_SIZE = 50  # Default API pagination
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'DMP-Platform/2.0',
            'Accept': 'application/json'
        })
        self.call_timestamps = []
        self.cache = {}  # Simple response caching
    
    def _wait_for_rate_limit(self):
        """Enforce rate limiting"""
        now = time.time()
        # Remove calls older than 1 minute
        self.call_timestamps = [t for t in self.call_timestamps if now - t < 60]
        
        if len(self.call_timestamps) >= self.RATE_LIMIT:
            sleep_time = 60 - (now - self.call_timestamps[0])
            if sleep_time > 0:
                logger.info(f"PGS rate limit hit, sleeping {sleep_time:.1f}s")
                time.sleep(sleep_time)
        
        self.call_timestamps.append(now)
    
    def search_scores_by_trait(self, trait_efo: str, ancestry: str = "EUR", include_performance: bool = True) -> List[Dict]:
        """Enhanced trait search with performance metrics"""
        cache_key = f"scores_{trait_efo}_{ancestry}"
        if cache_key in self.cache:
            return self.cache[cache_key]
            
        self._wait_for_rate_limit()
        
        try:
            # Get scores
            score_params = {
                'trait_efo': trait_efo,
                'limit': self.PAGE_SIZE,
                'include_children': True
            }
            
            score_resp = self.session.get(f"{self.BASE_URL}score/search/", params=score_params, timeout=30)
            score_resp.raise_for_status()
            score_data = score_resp.json()
            results = score_data.get('results', [])
            
            # Get performance metrics if requested
            if include_performance:
                perf_results = []
                for score in results[:5]:  # Limit to top 5
                    perf_data = self.get_performance_metrics(score['id'])
                    if perf_data:
                        score['performance_metrics'] = perf_data
                        # Add best metric to top level for easy access
                        if len(perf_data) > 0:
                            score['best_metric'] = max(
                                perf_data,
                                key=lambda x: float(x['value']) if x['value'] and x['value'].replace('.','',1).isdigit() else 0
                            )
                    if perf_data:
                        score['performance_metrics'] = perf_data
                    perf_results.append(score)
                results = perf_results
            
            # Filter and rank by ancestry and quality
            filtered_results = self._filter_and_rank_scores(results, ancestry)
            
            logger.info(f"Found {len(filtered_results)} PGS scores for trait {trait_efo}")
            self.cache[cache_key] = filtered_results
            return filtered_results
            
        except Exception as e:
            logger.error(f"PGS API call failed for trait {trait_efo}: {e}")
            return []
    
    def get_performance_metrics(self, pgs_id: str) -> List[Dict]:
        """Get performance metrics for a PGS score (always returns a list)"""
        cache_key = f"perf_{pgs_id}"
        if cache_key in self.cache:
            return self.cache[cache_key]
            
        self._wait_for_rate_limit()
        
        try:
            response = self.session.get(
                f"{self.BASE_URL}performance/search",
                params={'associated_pgs_id': pgs_id},
                timeout=30
            )
            response.raise_for_status()
            
            data = response.json()
            metrics = data.get('results', [])
            
            # Filter to only include relevant metrics
            filtered_metrics = []
            for metric in metrics:
                if metric.get('performance_metrics'):
                    filtered_metrics.append({
                        'metric_type': metric.get('performance_metrics', {}).get('type'),
                        'value': metric.get('performance_metrics', {}).get('estimate'),
                        'unit': metric.get('performance_metrics', {}).get('unit'),
                        'sample_size': metric.get('sample_size'),
                        'ancestry': metric.get('ancestry_distribution') or metric.get('ancestry')
                    })
            
            logger.info(f"Found {len(filtered_metrics)} performance metrics for PGS {pgs_id}")
            self.cache[cache_key] = filtered_metrics
            return filtered_metrics
            
        except Exception as e:
            logger.error(f"Failed to get performance metrics for {pgs_id}: {e}")
            return []  # Always return empty list on error

    def _filter_and_rank_scores(self, scores: List[Dict], patient_ancestry: str) -> List[Dict]:
        """Filter and rank scores by ancestry and quality"""
        
        # Ancestry priority mapping
        ancestry_weights = {
            'EUR': {'EUR': 1.0, 'European': 1.0, 'Multi': 0.7, 'NR': 0.3},
            'EAS': {'EAS': 1.0, 'East Asian': 1.0, 'Multi': 0.7, 'EUR': 0.5, 'NR': 0.3},
            'AFR': {'AFR': 1.0, 'African': 1.0, 'Multi': 0.7, 'EUR': 0.4, 'NR': 0.3},
            'SAS': {'SAS': 1.0, 'South Asian': 1.0, 'Multi': 0.7, 'EUR': 0.5, 'NR': 0.3},
        }
        
        weights = ancestry_weights.get(patient_ancestry, ancestry_weights['EUR'])
        
        scored_results = []
        for score in scores:
            # Calculate ancestry score
            ancestry_dist = score.get('ancestry_distribution', {})
            ancestry_score = 0
            for anc, weight in weights.items():
                if anc in str(ancestry_dist):
                    ancestry_score = max(ancestry_score, weight)
            
            # Calculate quality score based on variant count
            variant_count = score.get('variants_number', 0)
            if variant_count > 100000:
                quality_score = 1.0
            elif variant_count > 10000:
                quality_score = 0.8
            elif variant_count > 1000:
                quality_score = 0.6
            else:
                quality_score = 0.4
            
            # Boost known high-quality scores
            score_id = score.get('id', '')
            boost = 0
            if score_id in ['PGS000014', 'PGS000330', 'PGS000713']:  # Known good T2D scores
                boost = 0.3
            elif score_id in ['PGS000021', 'PGS000024']:  # Known good T1D scores  
                boost = 0.3
            
            total_score = (ancestry_score * 0.6) + (quality_score * 0.3) + boost
            
            scored_results.append({
                **score,
                'dmp_quality_score': total_score,
                'dmp_ancestry_match': ancestry_score,
                'dmp_variant_quality': quality_score
            })
        
        # Sort by total score and return top 5
        scored_results.sort(key=lambda x: x['dmp_quality_score'], reverse=True)
        return scored_results[:5]
# Add this to your existing genetics plugin
# Place it right after the PGSCatalogClient class

class PharmGKBClient:
    """Enhanced PharmGKB API client with full endpoint support"""
    
    BASE_URL = "https://api.pharmgkb.org/v1/"
    CACHE_TTL = 3600  # 1 hour cache
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'DMP-Platform/2.0',
            'Accept': 'application/json'
        })
        self.cache = {}
    
    def get_drug_gene_interactions(self, gene_symbols: List[str], include_clinical: bool = True) -> List[Dict]:
        """Enhanced drug-gene interaction search with clinical annotations"""
        cache_key = f"interactions_{'_'.join(sorted(gene_symbols))}"
        if cache_key in self.cache:
            return self.cache[cache_key]
            
        try:
            interactions = []
            for gene in gene_symbols:
                # Get drug labels
                label_resp = self.session.get(
                    f"{self.BASE_URL}data/gene/{gene}/drugLabels",
                    timeout=30
                )
                if label_resp.status_code == 200:
                    label_data = label_resp.json()
                    interactions.extend(label_data.get('data', []))
                
                # Get clinical annotations if requested
                if include_clinical:
                    clinical_resp = self.session.get(
                        f"{self.BASE_URL}data/gene/{gene}/clinicalAnnotations",
                        timeout=30
                    )
                    if clinical_resp.status_code == 200:
                        clinical_data = clinical_resp.json()
                        interactions.extend(clinical_data.get('data', []))
            
            logger.info(f"Found {len(interactions)} drug-gene interactions for {gene_symbols}")
            self.cache[cache_key] = interactions
            return interactions
        except Exception as e:
            logger.error(f"PharmGKB API call failed: {e}")
            return []
    
    def get_diabetes_pharmacogenomics(self) -> Dict:
        """Get diabetes-specific pharmacogenomic data"""
        diabetes_genes = ['TCF7L2', 'PPARG', 'KCNJ11', 'ABCC8', 'HNF1A', 'HNF4A']
        
        all_interactions = []
        for gene in diabetes_genes:
            interactions = self.get_drug_gene_interactions([gene])
            all_interactions.extend(interactions)
        
        return {
            'gene_count': len(diabetes_genes),
            'interactions': all_interactions[:10],  # Top 10
            'diabetes_specific': True
        }
        
    def fetch_drug_interactions(self, genes: List[str]) -> List[Dict]:
        """Fetch drug-gene interactions (alias for get_drug_gene_interactions)"""
        return self.get_drug_gene_interactions(genes, include_clinical=True)
        
class GeneticDataExtractor:
    """Extracts genetic info from your existing OCR output"""
    
    @staticmethod
    def extract_genetic_info(ocr_text: str) -> Dict:
        """Extract genetic information from OCR text"""
        
        genetic_info = {
            'snp_count': 0,
            'ancestry': 'Unknown',
            'quality_score': 'Low',
            'test_provider': 'Unknown',
            'has_genetic_data': False
        }
        
        if not ocr_text or len(ocr_text.strip()) < 50:
            return genetic_info
        
        ocr_lower = ocr_text.lower()
        
        # Extract SNP count
        snp_patterns = [
            r'(\d{1,3}(?:,\d{3})*)\s*(?:snps?|variants?|markers?)',
            r'(?:analyzed|genotyped|called)\s*(\d{1,3}(?:,\d{3})*)',
            r'(\d{1,3}(?:,\d{3})*)\s*(?:genetic\s*variants|positions)'
        ]
        
        for pattern in snp_patterns:
            matches = re.findall(pattern, ocr_lower)
            if matches:
                try:
                    snp_count = int(matches[0].replace(',', ''))
                    if snp_count > 1000:  # Reasonable threshold
                        genetic_info['snp_count'] = snp_count
                        genetic_info['has_genetic_data'] = True
                        break
                except:
                    continue
        
        # Extract ancestry
        ancestry_keywords = {
            'european': 'EUR',
            'caucasian': 'EUR', 
            'east asian': 'EAS',
            'asian': 'EAS',
            'african': 'AFR',
            'south asian': 'SAS',
            'hispanic': 'AMR',
            'latino': 'AMR'
        }
        
        for keyword, code in ancestry_keywords.items():
            if keyword in ocr_lower:
                genetic_info['ancestry'] = code
                break
        
        # Extract test provider
        providers = ['23andme', 'ancestrydna', 'myheritage', 'familytreedna', 'living dna', 'nebula']
        for provider in providers:
            if provider.replace(' ', '') in ocr_lower.replace(' ', ''):
                genetic_info['test_provider'] = provider.title()
                break
        
        # Determine quality score
        if genetic_info['snp_count'] > 500000:
            genetic_info['quality_score'] = 'High'
        elif genetic_info['snp_count'] > 100000:
            genetic_info['quality_score'] = 'Medium'
        elif genetic_info['snp_count'] > 10000:
            genetic_info['quality_score'] = 'Low'
        
        logger.info(f"Extracted genetic info: {genetic_info}")
        return genetic_info


class DMPGeneticsAnalyzer:
    """Main analyzer - uses your existing DeepSeek integration"""
    
    def __init__(self, deepseek_function: Optional[Callable[[str], Awaitable[str]]] = None):
        self.pgs_client = PGSCatalogClient()
        self.pharmgkb_client = PharmGKBClient()
        self.deepseek_function = deepseek_function or self._default_deepseek_function
        
        # Trait mapping for doctor questions
        self.trait_keywords = {
            'διαβήτη': ['EFO_0000400', 'EFO_0001359'],  # T2D, T1D
            'diabetes': ['EFO_0000400', 'EFO_0001359'],
            'τύπου 1': ['EFO_0001359'],  # T1D only
            'τύπου 2': ['EFO_0000400'],  # T2D only
            'παχυσαρκία': ['EFO_0001073'],  # Obesity
            'obesity': ['EFO_0001073'],
            'βάρος': ['EFO_0004340'],  # BMI
            'καρδιά': ['EFO_0000378'],  # Cardiovascular
            'heart': ['EFO_0000378'],
            'υπέρταση': ['EFO_0000537'],  # Hypertension
            'χοληστερόλη': ['EFO_0004611'],  # Cholesterol
            # Medication-related terms
            'φάρμακο': ['EFO_0000508'],  # Drug response
            'φαρμακο': ['EFO_0000508'],
            'φαρμακευτικ': ['EFO_0000508'],
            'φαρμακοθεραπεία': ['EFO_0000508'],
            'warfarin': ['EFO_0000508'],
            'μεθορτρεξάτη': ['EFO_0000508'],
            'metformin': ['EFO_0000508'],
            'insulin': ['EFO_0000508']
        }
        
    async def _default_deepseek_function(self, prompt: str) -> str:
        """Fallback function if no DeepSeek function is provided"""
        # Simulate async processing
        await asyncio.sleep(0.1)
        return f"Mock response to genetic prompt: {prompt}"
    
    def get_genetic_info_from_ocr(self, patient_id: str, ocr_text: str) -> Dict:
        """Process OCR text to extract genetic information"""
        genetic_info = GeneticDataExtractor.extract_genetic_info(ocr_text)
        
        # You can store this in your existing database
        # using your existing database functions
        
        return {
            'status': 'success' if genetic_info['has_genetic_data'] else 'no_genetic_data',
            'genetic_info': genetic_info,
            'message': f"Βρέθηκαν {genetic_info['snp_count']:,} γενετικές παραλλαγές" if genetic_info['has_genetic_data'] else "Δεν βρέθηκαν γενετικά δεδομένα"
        }
    
    async def answer_genetic_question(self, patient_id: str, question: str) -> Dict:
        """
        Main function - answer doctor's genetic question
        
        Args:
            patient_id: The patient ID
            question: Doctor's question in Greek
        
        Returns:
            Dict with formatted answer for chat interface
            
        Handles both genetic risk and medication-related questions
        """
        
        try:
            # Step 1: Get patient's genetic data from your existing system
            genetic_info = await self._get_patient_genetic_data(patient_id)
            
            if not genetic_info or not genetic_info.get('has_genetic_data'):
                return {
                    "status": "no_genetic_data",
                    "message": "Ο ασθενής δεν έχει ανεβάσει γενετική εξέταση ακόμα.",
                    "action": "Παρακαλώ ζητήστε από τον ασθενή να ανεβάσει το γενετικό του τεστ."
                }
            
            # Step 2: Check if this is a medication question
            medication_keywords = ['warfarin', 'φάρμακο', 'φαρμακο', 'φαρμακευτικ', 'φαρμακοθεραπεία',
                                 'μεθορτρεξάτη', 'metformin', 'insulin']
            
            if any(keyword in question.lower() for keyword in medication_keywords):
                # Use PharmGKB for medication questions
                pharmgkb = PharmGKBClient()
                interactions = pharmgkb.get_drug_gene_interactions(['TCF7L2', 'PPARG', 'KCNJ11'])
                
                if interactions:
                    return {
                        "status": "success",
                        "answer": self._format_pharmgkb_response(interactions, question),
                        "source": "PharmGKB"
                    }
            
            # Not a medication question - proceed with PGS analysis
            needed_traits = self._extract_traits_from_question(question)
            
            # Step 3: Fetch PGS scores from catalog
            all_pgs_scores = []
            for trait_efo in needed_traits:
                scores = self.pgs_client.search_scores_by_trait(trait_efo, genetic_info.get('ancestry', 'EUR'))
                all_pgs_scores.extend(scores)
            
            if not all_pgs_scores:
                return {
                    "status": "no_pgs_data",
                    "message": "Δεν βρέθηκαν κατάλληλα PGS scores για αυτή την ερώτηση.",
                    "action": "Δοκιμάστε μια πιο γενική ερώτηση."
                }
            
            # Step 4: Use your existing DeepSeek integration for analysis
            analysis_prompt = self._create_analysis_prompt(question, genetic_info, all_pgs_scores)
            
            # Call the stored DeepSeek function
            ai_response = await self.deepseek_function(analysis_prompt)
            
            # Step 5: Parse AI response to SimpleGeneticResult
            result = self._parse_ai_response(ai_response, all_pgs_scores)
            
            # Step 6: Format for chat interface
            formatted_answer = self._format_answer_for_chat(result)
            
            return {
                "status": "success",
                "answer": formatted_answer,
                "raw_result": asdict(result)
            }
            
        except Exception as e:
            logger.error(f"Failed to answer genetic question: {e}")
            return {
                "status": "error", 
                "message": f"Σφάλμα ανάλυσης: {str(e)}"
            }
    
    async def _get_patient_genetic_data(self, patient_id: str) -> Optional[Dict]:
        """
        Get patient's genetic data from MongoDB
        
        Args:
            patient_id: The patient ID string
            
        Returns:
            Dict with genetic data or None if not found
        """
        from utils.db import get_db
        from bson.objectid import ObjectId
        from bson.errors import InvalidId
        import asyncio
        
        def sync_find_one(db, query):
            """Synchronous wrapper for find_one operation"""
            return db.genetic_data.find_one(query)
            
        try:
            db = get_db()
            if db is None:
                logger.error("Database connection failed")
                return None
                
            # Convert string ID to ObjectId
            try:
                patient_oid = ObjectId(patient_id)
            except InvalidId:
                logger.error(f"Invalid patient ID format: {patient_id}")
                return None
                
            # Run synchronous operation in executor to get patient document
            loop = asyncio.get_event_loop()
            try:
                patient_doc = await loop.run_in_executor(
                    None,
                    sync_find_one,
                    db.patients,
                    {"_id": patient_oid}
                )
                
                if patient_doc:
                    logger.debug(f"Found patient document for {patient_oid}")
                    if 'genetic_data' in patient_doc and patient_doc['genetic_data']:
                        logger.info(f"Found genetic data for patient {patient_oid}")
                        return patient_doc['genetic_data']
                    else:
                        logger.warning(f"Patient {patient_oid} exists but has no genetic_data field or it's empty")
                        logger.debug(f"Patient document keys: {list(patient_doc.keys())}")
                else:
                    logger.warning(f"No patient found with ID: {patient_oid}")
                    
                return None
            except Exception as e:
                logger.error(f"Error retrieving genetic data: {str(e)}")
                return None
            return None
            
        except Exception as e:
            logger.error(f"Error fetching genetic data: {e}")
            return None
    
    def _extract_traits_from_question(self, question: str) -> List[str]:
        """Extract EFO trait IDs from doctor's question"""
        question_lower = question.lower()
        found_traits = set()
        
        for keyword, trait_ids in self.trait_keywords.items():
            if keyword in question_lower:
                found_traits.update(trait_ids)
        
        # Default to diabetes if no specific traits found
        if not found_traits:
            found_traits.update(['EFO_0000400', 'EFO_0001359'])  # T2D and T1D
        
        return list(found_traits)
    
    def _create_analysis_prompt(self, question: str, genetic_info: Dict, pgs_scores: List[Dict]) -> str:
        """Create prompt for your existing DeepSeek integration"""
        
        # Prepare PGS scores summary
        pgs_summary = self._prepare_pgs_summary(pgs_scores)
        
        prompt = f"""
        Είσαι έμπειρος γιατρός γενετικής που εξηγεί σε συνάδελφο με απλά λόγια.

        ΕΡΩΤΗΣΗ ΓΙΑΤΡΟΥ: "{question}"

        ΓΕΝΕΤΙΚΑ ΔΕΔΟΜΕΝΑ ΑΣΘΕΝΗ:
        - Καταγωγή: {genetic_info.get('ancestry', 'Unknown')}
        - SNPs διαθέσιμα: {genetic_info.get('snp_count', 0):,}
        - Ποιότητα δεδομένων: {genetic_info.get('quality_score', 'Unknown')}
        - Test provider: {genetic_info.get('test_provider', 'Unknown')}

        ΔΙΑΘΕΣΙΜΑ PGS SCORES (Polygenic Risk Scores):
        {pgs_summary}

        Δώσε ΑΠΛΗ απάντηση που να καταλαβαίνει κάθε γιατρός. Απάντησε ΜΟΝΟ σε JSON format:

        {{
            "condition": "<η νόσος που ρωτάει>",
            "risk_level": "<ΧΑΜΗΛΟΣ/ΜΕΤΡΙΟΣ/ΥΨΗΛΟΣ/ΠΟΛΥ ΥΨΗΛΟΣ>",
            "percentile": <αριθμός 0-100>,
            "confidence": "<Υψηλή/Μέτρια/Χαμηλή>",
            "recommendations": [
                "<σύσταση 1>",
                "<σύσταση 2>", 
                "<σύσταση 3>"
            ],
            "explanation": "<σύντομη εξήγηση 2-3 προτάσεις>",
            "emoji": "<🟢 για χαμηλό, 🟡 για μέτριο, 🔴 για υψηλό κίνδυνο>"
        }}

        ΣΗΜΑΝΤΙΚΟΙ ΚΑΝΟΝΕΣ:
        - Μην αναφέρεις PGS IDs ή τεχνικά στοιχεία
        - Κάνε τα πολύπλοκα απλά
        - Δώσε συγκεκριμένες κλινικές συστάσεις
        - Αν δεν υπάρχουν αρκετά δεδομένα, πες "Χαμηλή" εμπιστοσύνη
        - Βάσισε την ανάλυση στα PGS scores που παρέχονται
        """
        
        return prompt
    
    def _prepare_pgs_summary(self, pgs_scores: List[Dict]) -> str:
        """Prepare PGS scores summary for AI"""
        if not pgs_scores:
            return "Δεν βρέθηκαν σχετικά PGS scores"
        
        summary_lines = []
        for i, score in enumerate(pgs_scores[:3], 1):  # Top 3 scores
            variants = score.get('variants_number', 0)
            quality = score.get('dmp_quality_score', 0)
            name = score.get('name', score.get('id', 'Unknown'))
            trait = score.get('trait_reported', 'Unknown')
            
            summary_lines.append(
                f"{i}. Score: {name}\n"
                f"   - Trait: {trait}\n"
                f"   - Variants: {variants:,}\n"
                f"   - Quality: {quality:.2f}/1.0\n"
                f"   - Ancestry match: {score.get('dmp_ancestry_match', 0):.2f}/1.0"
            )
        
        return "\n".join(summary_lines)
    
    def _parse_ai_response(self, ai_response: str, pgs_scores: List[Dict]) -> SimpleGeneticResult:
        """Parse AI response to SimpleGeneticResult"""
        
        try:
            # Extract JSON from AI response
            json_match = re.search(r'\{.*\}', ai_response, re.DOTALL)
            if json_match:
                result_data = json.loads(json_match.group())
                
                return SimpleGeneticResult(
                    condition=result_data.get('condition', 'Unknown'),
                    risk_level=result_data.get('risk_level', 'ΜΕΤΡΙΟΣ'),
                    percentile=result_data.get('percentile', 50),
                    confidence=result_data.get('confidence', 'Μέτρια'),
                    recommendations=result_data.get('recommendations', []),
                    explanation=result_data.get('explanation', ''),
                    emoji=result_data.get('emoji', '🟡'),
                    pgs_scores_used=[score.get('id', 'Unknown') for score in pgs_scores[:3]]
                )
            else:
                raise ValueError("No valid JSON in AI response")
                
        except Exception as e:
            logger.error(f"Failed to parse AI response: {e}")
            return SimpleGeneticResult(
                condition="Unknown",
                risk_level="ΜΕΤΡΙΟΣ", 
                percentile=50,
                confidence="Χαμηλή",
                recommendations=["Απαιτείται περισσότερη ανάλυση"],
                explanation="Δεν ήταν δυνατή η πλήρης ανάλυση των δεδομένων.",
                emoji="🟡"
            )
    
    def _format_pharmgkb_response(self, interactions: List[Dict], question: str) -> str:
        """Format PharmGKB drug-gene interaction response for chat"""
        relevant = []
        for interaction in interactions:
            if any(keyword in question.lower() for keyword in interaction.get('drug', '').lower().split()):
                relevant.append(interaction)
        
        if not relevant:
            return "Δεν βρέθηκαν σχετικές φαρμακογονιδιακές αλληλεπιδράσεις για αυτό το φάρμακο."
            
        response = ["🔬 **Φαρμακογονιδιακές Αλληλεπιδράσεις:**"]
        for interaction in relevant[:3]:  # Limit to top 3
            drug = interaction.get('drug', 'Unknown')
            gene = interaction.get('gene', 'Unknown')
            effect = interaction.get('effect', 'Unknown')
            response.append(
                f"• **{drug}** με **{gene}**: {effect}\n"
                f"  - Clinical significance: {interaction.get('clinical_significance', 'Unknown')}"
            )
            
        return "\n\n".join(response)

    def _format_answer_for_chat(self, result: SimpleGeneticResult) -> str:
        """Format AI result for chat interface"""
        
        recommendations_text = "\n".join(f"• {rec}" for rec in result.recommendations)
        
        formatted = f"""
{result.emoji} **{result.risk_level} κίνδυνος** για {result.condition}

📊 **Εκατοστημόριο:** {result.percentile}ο (υψηλότερος από {result.percentile}% του πληθυσμού)

🎯 **Εμπιστοσύνη ανάλυσης:** {result.confidence}

📋 **Συστάσεις:**
{recommendations_text}

💡 **Εξήγηση:** {result.explanation}

🔬 *Βασίστηκε σε {len(result.pgs_scores_used or [])} validated PGS scores*
        """.strip()
        
        return formatted


    def analyze_genetic_data(self, ocr_text: str, question: str) -> Dict:
        """
        Analyze genetic data from OCR text without requiring patient ID
        
        Args:
            ocr_text: Text from genetic report OCR
            question: Doctor's question about genetic risk
            
        Returns:
            Analysis result in the same format as answer_genetic_question()
        """
        # Extract genetic info directly from OCR
        genetic_info = GeneticDataExtractor.extract_genetic_info(ocr_text)
        
        if not genetic_info.get('has_genetic_data'):
            return {
                "status": "no_genetic_data",
                "message": "Δεν βρέθηκαν γενετικά δεδομένα στο κείμενο OCR.",
                "action": "Παρακαλώ ελέγξτε το αρχείο OCR."
            }
            
        # Check if this is a medication question
        medication_keywords = ['warfarin', 'φάρμακο', 'φαρμακο', 'φαρμακευτικ',
                              'φαρμακοθεραπεία', 'μεθορτρεξάτη', 'metformin', 'insulin']
        
        if any(keyword in question.lower() for keyword in medication_keywords):
            interactions = self.pharmgkb_client.fetch_drug_interactions(['TCF7L2', 'PPARG', 'KCNJ11'])
            if interactions:
                return {
                    "status": "success",
                    "answer": self._format_pharmgkb_response(interactions, question),
                    "source": "PharmGKB"
                }
                
        # Proceed with PGS analysis for non-medication questions
        needed_traits = self._extract_traits_from_question(question)
        all_pgs_scores = []
        for trait_efo in needed_traits:
            scores = self.pgs_client.search_scores_by_trait(trait_efo, genetic_info.get('ancestry', 'EUR'))
            all_pgs_scores.extend(scores)
            
        if not all_pgs_scores:
            return {
                "status": "no_pgs_data",
                "message": "Δεν βρέθηκαν κατάλληλα PGS scores για αυτή την ερώτηση.",
                "action": "Δοκιμάστε μια πιο γενική ερώτηση."
            }
            
        # Use DeepSeek for analysis - always get string response
        analysis_prompt = self._create_analysis_prompt(question, genetic_info, all_pgs_scores)
        
        # Handle both async and sync cases
        if asyncio.iscoroutinefunction(self.deepseek_function):
            response_value = asyncio.run(self.deepseek_function(analysis_prompt))
        else:
            response_value = self.deepseek_function(analysis_prompt)
        
        # Ensure we have a string response
        ai_response = response_value if isinstance(response_value, str) else str(response_value)
        result = self._parse_ai_response(ai_response, all_pgs_scores)
        
        # Format for chat interface
        formatted_answer = self._format_answer_for_chat(result)
        
        return {
            "status": "success",
            "answer": formatted_answer,
            "raw_result": asdict(result)
        }

# Integration Functions for your existing Flask app
def add_genetics_to_existing_routes(app, analyzer: DMPGeneticsAnalyzer):
    """Add genetics functionality to your existing Flask routes"""
    
    @app.route('/api/genetics/analyze-ocr', methods=['POST'])
    async def analyze_genetic_ocr():
        """Process OCR output for genetic information"""
        from flask import request, jsonify
        
        data = request.get_json()
        patient_id = data.get('patient_id')
        ocr_text = data.get('ocr_text')
        
        if not patient_id or not ocr_text:
            return jsonify({"error": "Missing patient_id or ocr_text"}), 400
        
        result = analyzer.get_genetic_info_from_ocr(patient_id, ocr_text)
        return jsonify(result)
    
    @app.route('/api/genetics/ask', methods=['POST'])
    async def ask_genetic_question():
        """Doctor asks genetic question - uses your existing DeepSeek function"""
        from flask import request, jsonify
        
        data = request.get_json()
        patient_id = data.get('patient_id')
        question = data.get('question')
        
        if not patient_id or not question:
            return jsonify({"error": "Missing patient_id or question"}), 400
        
        # Use the analyzer with the pre-configured DeepSeek function
        result = await analyzer.answer_genetic_question(patient_id, question)
        return jsonify(result)


# Example usage with your existing system
async def integrate_with_existing_dmp(your_existing_deepseek_function):
    """Example of how to integrate with your existing DMP system"""
    
    # Initialize analyzer with DeepSeek function
    analyzer = DMPGeneticsAnalyzer(deepseek_function=your_existing_deepseek_function)
    
    # Example: Process OCR output
    genetic_info = analyzer.get_genetic_info_from_ocr(
        patient_id="patient_123",
        ocr_text="Your existing OCR output here..."
    )
    
    print("Genetic info extracted:", genetic_info)
    
    # Example: Answer doctor question using your existing DeepSeek
    if genetic_info['status'] == 'success':
        result = await analyzer.answer_genetic_question(
            patient_id="patient_123",
            question="Τι κίνδυνο έχει για διαβήτη;"
        )
        
        print("Genetic analysis result:", result)


if __name__ == "__main__":
    # Test the PGS API connection
    client = PGSCatalogClient()
    scores = client.search_scores_by_trait("EFO_0000400", "EUR")  # Test T2D scores
    print(f"Found {len(scores)} T2D scores")
    
    # Test genetic data extraction
    sample_ocr = "23andMe Genetic Report: 670,000 SNPs analyzed, European ancestry detected"
    genetic_info = GeneticDataExtractor.extract_genetic_info(sample_ocr)
    print("Extracted genetic info:", genetic_info)