import unittest
from unittest.mock import Mock, patch, MagicMock
from typing import List, Dict
from diabetes_backend.services.genetics_analyzer import PGSCatalogClient, PharmGKBClient, DMPGeneticsAnalyzer, SimpleGeneticResult

class TestPGSCatalogClient(unittest.TestCase):
    def setUp(self):
        self.client = PGSCatalogClient()
        self.client.session = MagicMock()
        self.client.session.get = MagicMock()
        self.client.cache = {}

    @patch('time.sleep')
    @patch('requests.Session.get')
    def test_get_performance_metrics(self, mock_sleep, mock_get):
        # Mock API response
        mock_response = MagicMock()
        mock_response.json.return_value = {
            'results': [{
                'performance_metrics': [{
                    'type': 'AUC',
                    'estimate': 0.85,
                    'unit': None
                }],
                'sample_size': 1000,
                'ancestry_distribution': 'European',
                'ancestry': 'European'
            }]
        }
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response

        # Test the method
        metrics: List[Dict] = self.client.get_performance_metrics('PGS000001')
        self.assertIsInstance(metrics, list)
        self.assertEqual(len(metrics), 1)
        self.assertEqual(metrics[0]['metric_type'], 'AUC')
        self.assertEqual(metrics[0]['value'], 0.85)
        self.assertEqual(metrics[0]['ancestry'], 'European')
        self.assertIn('perf_PGS000001', self.client.cache)

    @patch('requests.Session.get')
    def test_get_performance_metrics_error(self, mock_get):
        mock_get.side_effect = Exception("API error")
        metrics: List[Dict] = self.client.get_performance_metrics('PGS000001')
        self.assertIsInstance(metrics, list)
        self.assertEqual(len(metrics), 0)

class TestPharmGKBClient(unittest.TestCase):
    def setUp(self):
        self.client = PharmGKBClient()
        self.client.session = MagicMock()
        self.client.cache = {}
        # Use patch to properly mock instance method
        self.mock_get_drug_gene = MagicMock()
        self.client.get_drug_gene_interactions = self.mock_get_drug_gene

    def test_fetch_drug_interactions_success(self):
        """Test successful retrieval of drug-gene interactions"""
        # Mock API response
        mock_response = [{
            "gene": "VKORC1",
            "drug": "Warfarin",
            "interaction": "Increased risk of bleeding",
            "evidenceLevel": "1A"
        }]
        self.mock_get_drug_gene.return_value = mock_response
        
        interactions = self.client.fetch_drug_interactions(["VKORC1"])
        
        self.assertEqual(len(interactions), 1)
        self.assertEqual(interactions[0]["gene"], "VKORC1")
        self.assertEqual(interactions[0]["drug"], "Warfarin")
        self.mock_get_drug_gene.assert_called_once_with(["VKORC1"], include_clinical=True)

    def test_fetch_drug_interactions_failure(self):
        """Test handling of API failure"""
        self.mock_get_drug_gene.return_value = []
        
        interactions = self.client.fetch_drug_interactions(["VKORC1"])
        
        self.assertEqual(interactions, [])
        self.mock_get_drug_gene.assert_called_once_with(["VKORC1"], include_clinical=True)

    def test_diabetes_specific_filtering(self):
        """Test filtering for diabetes-relevant interactions"""
        self.mock_get_drug_gene.return_value = [
            {"gene": "VKORC1", "drug": "Warfarin", "interaction": "Bleeding risk"},
            {"gene": "SLC22A1", "drug": "Metformin", "interaction": "Efficacy reduction"},
            {"gene": "CYP2C9", "drug": "Sulfonylureas", "interaction": "Hypoglycemia risk"},
            {"gene": "CYP2C9", "drug": "Glipizide", "interaction": "Hypoglycemia risk"}
        ]
        
        interactions = self.client.fetch_drug_interactions(["VKORC1", "SLC22A1", "CYP2C9"])
        
        # Should filter to only diabetes-relevant drugs
        self.assertEqual(len(interactions), 4)
        self.assertEqual(interactions[0]["drug"], "Metformin")
        self.assertEqual(interactions[1]["drug"], "sulfonylureas")
        self.assertEqual(interactions[2]["drug"], "Glipizide")
        self.mock_get_drug_gene.assert_called_once_with(
            ["VKORC1", "SLC22A1", "CYP2C9"], include_clinical=True
        )

class TestGeneticIntegration(unittest.TestCase):
    @patch('diabetes_backend.services.genetics_analyzer.PGSCatalogClient.search_scores_by_trait')
    @patch('diabetes_backend.services.genetics_analyzer.PharmGKBClient.fetch_drug_interactions')
    @patch('diabetes_backend.services.deepseek_integration.ask_genetic_question')
    def test_full_analysis_flow(self, mock_ask, mock_pharm, mock_pgs):
        """Test integration from genetic data to clinical recommendations"""
        # Setup mocks
        mock_pgs.return_value = [{"id": "PGS000001", "score": 0.85, "percentile": 92}]
        mock_pharm.return_value = [{"gene": "CYP2C9", "drug": "Sulfonylureas", "interaction": "Hypoglycemia risk"}]
        
        # Mock AI response as dictionary with unified format
        mock_ai_response = {
            "response": "Genetic analysis indicates high risk",
            "sources_used": ["PGS Catalog", "PharmGKB", "PubMed"],
            "confidence": "High",
            "condition": "Type 2 Diabetes",
            "risk_level": "High",
            "percentile": 92,
            "recommendations": [
                "Lifestyle modification",
                "Metformin therapy"
            ],
            "explanation": "High polygenic risk score combined with drug interactions",
            "emoji": "⚠️"
        }
        mock_ask.return_value = mock_ai_response
        
        analyzer = DMPGeneticsAnalyzer()
        result = analyzer.analyze_genetic_data(
            ocr_text="...genetic report text...",
            question="What diabetes risks and treatments are indicated?"
        )
        
        # Access properties of SimpleGeneticResult instance
        self.assertEqual(result['raw_result']['risk_level'], "High")
        self.assertEqual(len(result['raw_result']['recommendations']), 2)
        self.assertEqual(result['raw_result']['condition'], "Type 2 Diabetes")
        self.assertEqual(result['raw_result']['sources_used'], ["PGS Catalog", "PharmGKB", "PubMed"])
        self.assertEqual(result['raw_result']['confidence'], "High")

    @patch('diabetes_backend.services.genetics_analyzer.PGSCatalogClient.search_scores_by_trait')
    @patch('diabetes_backend.services.genetics_analyzer.PharmGKBClient.fetch_drug_interactions')
    @patch('diabetes_backend.services.deepseek_integration.ask_genetic_question')
    def test_greek_polygenic_score_query(self, mock_ask, mock_pharm, mock_pgs):
        """Test Greek terminology recognition for polygenic score queries"""
        # Setup mocks
        mock_pgs.return_value = []  # No PGS scores found
        mock_pharm.return_value = []
        
        # Mock AI response with Greek error message
        mock_ai_response = {
            "response": "Δεν βρέθηκαν δεδομένα για πολυγονιδιακά σκορ (PGS) από το PGS Catalog στα διαθέσιμα έγγραφα του ασθενούς.",
            "sources_used": ["PGS Catalog"],
            "confidence": "Medium"
        }
        mock_ask.return_value = mock_ai_response
        
        analyzer = DMPGeneticsAnalyzer()
        result = analyzer.analyze_genetic_data(
            ocr_text="...genetic report text...",
            question="Μπορείς να βρεις πολυγονιδιακά σκορ για διαβήτη τύπου 1;"
        )
        
        # Verify Greek response is returned
        self.assertIn("Δεν βρέθηκαν δεδομένα", result['raw_result']['response'])
        self.assertEqual(result['raw_result']['sources_used'], ["PGS Catalog"])
        self.assertEqual(result['raw_result']['confidence'], "Medium")

    @patch('diabetes_backend.services.genetics_analyzer.PGSCatalogClient.search_scores_by_trait')
    @patch('diabetes_backend.services.genetics_analyzer.PharmGKBClient.fetch_drug_interactions')
    @patch('diabetes_backend.services.deepseek_integration.ask_genetic_question')
    def test_function_calling_trigger(self, mock_ask, mock_pharm, mock_pgs):
        """Test that function calls are properly triggered"""
        # Setup mocks
        mock_pgs.return_value = []
        mock_pharm.return_value = []
        
        # Mock AI response with function call simulation
        mock_ai_response = {
            "response": "Function calls detected: get_pgs_scores",
            "sources_used": ["PGS Catalog"],
            "confidence": "High"
        }
        mock_ask.return_value = mock_ai_response
        
        analyzer = DMPGeneticsAnalyzer()
        result = analyzer.analyze_genetic_data(
            ocr_text="...genetic report text...",
            question="Πολυγονιδιακά σκορ για διαβήτη τύπου 2"
        )
        
        # Verify function calling was triggered
        self.assertIn("Function calls detected", result['raw_result']['response'])
        self.assertIn("get_pgs_scores", result['raw_result']['response'])
        self.assertEqual(result['raw_result']['sources_used'], ["PGS Catalog"])
        self.assertEqual(result['raw_result']['confidence'], "High")
    @patch('diabetes_backend.services.genetics_analyzer.PGSCatalogClient.search_scores_by_trait')
    @patch('diabetes_backend.services.genetics_analyzer.PharmGKBClient.fetch_drug_interactions')
    @patch('diabetes_backend.services.deepseek_integration.ask_genetic_question')
    def test_unified_response_format(self, mock_ask, mock_pharm, mock_pgs):
        """Test unified response format with multiple sources"""
        # Setup mocks
        mock_pgs.return_value = [{"id": "PGS000001", "score": 0.85, "percentile": 92}]
        mock_pharm.return_value = [{"gene": "CYP2C9", "drug": "Sulfonylureas", "interaction": "Hypoglycemia risk"}]
        
        # Mock AI response as dictionary with unified format
        mock_ai_response = {
            "response": "Test response with multiple sources",
            "sources_used": ["PGS Catalog", "PubMed"],
            "confidence": "High"
        }
        mock_ask.return_value = mock_ai_response
        
        analyzer = DMPGeneticsAnalyzer()
        result = analyzer.analyze_genetic_data(
            ocr_text="...genetic report text...",
            question="Test unified format"
        )
        
        # Verify unified response format
        self.assertEqual(result['raw_result']['response'], "Test response with multiple sources")
        self.assertEqual(result['raw_result']['sources_used'], ["PGS Catalog", "PubMed"])
        self.assertEqual(result['raw_result']['confidence'], "High")
        
if __name__ == '__main__':
    unittest.main()