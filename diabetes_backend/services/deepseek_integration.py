"""
DeepSeek RAG Integration for Diabetes Management Platform
========================================================

This module integrates the DeepSeek RAG system with the DMP platform.
"""

import os
import json
import logging
import time
import requests
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

# API Configuration
DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY")
DEEPSEEK_API_URL = os.environ.get("DEEPSEEK_API_URL")
DEEPSEEK_API_TIMEOUT = 90  # seconds
DEEPSEEK_MAX_RETRIES = 3
DEEPSEEK_RETRY_DELAY = 1  # initial delay in seconds

async def ask_rag_question(prompt: str, genetic_context: Optional[Dict] = None) -> str:
    """
    Send a question to DeepSeek API with RAG context
    
    Args:
        prompt: The prompt to send to DeepSeek
        genetic_context: Optional dict with PGS/PharmGKB data from genetics_analyzer
        
    Returns:
        str: The AI response formatted for clinical use
    """
    if not DEEPSEEK_API_KEY or not DEEPSEEK_API_URL:
        logger.error("DeepSeek API configuration missing")
        return "AI service is not configured properly."
    
    try:
        headers = {
            'Authorization': f'Bearer {DEEPSEEK_API_KEY}',
            'Content-Type': 'application/json'
        }
        
        # Prepare messages with genetic context, PubMed RAG, and function tools
        messages = [
            {"role": "system", "content": """You are a clinical decision support system specializing in diabetes management and genetics, serving Greek-speaking patients.
Your responses MUST be evidence-based and clinically accurate.

KEY TERMS IN GREEK:
- Polygenic scores: πολυγονιδιακά σκορ
- Diabetes: διαβήτης (τύπου 1, τύπου 2)
- Genetic risk: γενετικός κίνδυνος

RULES FOR RESPONDING:
1. Integrate data from ALL sources: PGS Catalog + PharmGKB + PubMed RAG
2. Recognize Greek medical terminology (e.g. "πολυγονιδιακά σκορ" = polygenic scores)
3. Use simple medical language that doctors can understand
4. Always mention confidence levels and limitations
5. For diabetes genetics, focus on actionable recommendations
6. NEVER guess or invent medical information
7. If uncertain, clearly state limitations
8. For genetic risk scores, provide percentiles and clinical context
9. For drug-gene interactions, highlight diabetes-relevant findings
10. For treatment questions, combine genetic data with PubMed evidence
11. ALWAYS respond in JSON format with the following structure:
    {
        "response": "Your analysis text here",
        "sources_used": ["PGS Catalog", "PharmGKB", "PubMed"],
        "confidence": "High/Medium/Low",
        // Optional fields:
        "condition": "Type 2 Diabetes",
        "risk_level": "High",
        "percentile": 92,
        "recommendations": ["Lifestyle changes", "Metformin"],
        "explanation": "Detailed explanation",
        "emoji": "⚠️"
    }
    The ONLY required fields are "response", "sources_used", and "confidence"

FUNCTION TOOLS AVAILABLE:
- get_pgs_scores: Retrieve polygenic risk scores (πολυγονιδιακά σκορ) for diabetes from PGS Catalog
- fetch_drug_interactions: Get drug-gene interactions for medication-related questions

DATA SOURCES:
- PGS Catalog: Polygenic risk scores for diabetes and related conditions
- PharmGKB: Pharmacogenomic data for diabetes medications
- PubMed RAG: Latest research evidence from biomedical literature

Now analyze the following prompt:"""},
            {"role": "user", "content": prompt}
        ]

        # Add genetic context and PubMed RAG if provided
        if genetic_context:
            # Combine PGS, PharmGKB and PubMed RAG into a single context
            combined_context = {
                "pgs_scores": genetic_context.get("pgs_scores", []),
                "pharmgkb": genetic_context.get("pharmgkb", {}),
                "pubmed_rag": genetic_context.get("pubmed_rag", [])
            }
            messages.insert(1, {
                "role": "assistant",
                "content": f"INTEGRATED CONTEXT (PGS + PharmGKB + PubMed RAG):\n{json.dumps(combined_context, indent=2)}"
            })
            
        # Add function tools
        tools = [
            {
                "name": "fetch_drug_interactions",
                "description": "Get drug-gene interactions for medication-related questions",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "medication_name": {
                            "type": "string",
                            "description": "Name of the medication"
                        }
                    },
                    "required": ["medication_name"]
                }
            },
            {
                "name": "get_pgs_scores",
                "description": "Retrieve polygenic risk scores for diabetes from PGS Catalog",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "trait": {
                            "type": "string",
                            "description": "The trait to search for, e.g. 'diabetes'",
                            "default": "diabetes"
                        }
                    },
                    "required": []
                }
            }
        ]

        payload = {
            "model": "deepseek-chat",
            "messages": messages,
            "tools": tools,
            "tool_choice": "auto",
            "max_tokens": 2000,
            "temperature": 0.3,  # Lower temperature for more consistent medical responses
            "top_p": 0.9,
            "response_format": {"type": "json_object"}  # Enforce JSON output
        }
        
        logger.info("Sending request to DeepSeek API for genetics analysis...")
        
        last_error = None
        for attempt in range(DEEPSEEK_MAX_RETRIES):
            try:
                response = requests.post(
                    DEEPSEEK_API_URL,
                    headers=headers,
                    json=payload,
                    timeout=DEEPSEEK_API_TIMEOUT
                )
                
                # Handle rate limiting (429) and server errors (5xx)
                if response.status_code == 429:
                    retry_after = int(response.headers.get('Retry-After', DEEPSEEK_RETRY_DELAY * (attempt + 1)))
                    logger.warning(f"Rate limited - retrying after {retry_after}s (attempt {attempt + 1}/{DEEPSEEK_MAX_RETRIES})")
                    time.sleep(retry_after)
                    continue
                elif response.status_code >= 500:
                    logger.warning(f"Server error - retrying (attempt {attempt + 1}/{DEEPSEEK_MAX_RETRIES})")
                    time.sleep(DEEPSEEK_RETRY_DELAY * (attempt + 1))
                    continue
                    
                response.raise_for_status()
                
                response_data = response.json()
                logger.info("Received response from DeepSeek API for genetics.")
                
                if 'choices' in response_data and len(response_data['choices']) > 0:
                    ai_message = response_data['choices'][0].get('message', {})
                    content = ai_message.get('content', '')
                    tool_calls = ai_message.get('tool_calls', [])
                    
                    # Handle tool calls
                    if tool_calls:
                        # Handle tool execution
                        tool_responses = []
                        for call in tool_calls:
                            func_name = call['function']['name']
                            
                            if func_name == "get_pgs_scores":
                                # Simulate PGS data retrieval
                                tool_responses.append({
                                    "role": "tool",
                                    "content": "PGS Catalog query: No polygenic scores found in patient data",
                                    "tool_call_id": call['id']
                                })
                            elif func_name == "fetch_drug_interactions":
                                # Simulate drug interaction lookup
                                tool_responses.append({
                                    "role": "tool",
                                    "content": "PharmGKB query: No drug interactions found",
                                    "tool_call_id": call['id']
                                })
                        
                        # Resend with tool responses
                        messages.append(ai_message)
                        messages.extend(tool_responses)
                        
                        # Get final response with tool results
                        payload['messages'] = messages
                        response = requests.post(
                            DEEPSEEK_API_URL,
                            headers=headers,
                            json=payload,
                            timeout=DEEPSEEK_API_TIMEOUT
                        )
                        response.raise_for_status()
                        response_data = response.json()
                        
                        if 'choices' in response_data and len(response_data['choices']) > 0:
                            final_message = response_data['choices'][0].get('message', {})
                            final_content = final_message.get('content', '').strip()
                            
                            try:
                                response_json = json.loads(final_content)
                                
                                # Validate required fields
                                if "response" not in response_json:
                                    raise ValueError("Missing 'response' field in tool response")
                                if "sources_used" not in response_json:
                                    raise ValueError("Missing 'sources_used' field in tool response")
                                if "confidence" not in response_json:
                                    raise ValueError("Missing 'confidence' field in tool response")
                                    
                                return json.dumps(response_json)
                                
                            except (json.JSONDecodeError, ValueError) as e:
                                logger.error(f"Invalid tool response format: {e}")
                                return json.dumps({
                                    "response": final_content,
                                    "sources_used": ["AI"],
                                    "confidence": "Low",
                                    "error": str(e)
                                })
                        
                        return "AI model didn't return final response after tool execution"
                    
                    # Process unified response format
                    try:
                        response_json = json.loads(content)
                        
                        # Validate required fields
                        if "response" not in response_json:
                            raise ValueError("Missing 'response' field in API response")
                        if "sources_used" not in response_json:
                            raise ValueError("Missing 'sources_used' field in API response")
                        if "confidence" not in response_json:
                            raise ValueError("Missing 'confidence' field in API response")
                            
                        return json.dumps(response_json)
                        
                    except (json.JSONDecodeError, ValueError) as e:
                        logger.error(f"Invalid response format: {e}")
                        return json.dumps({
                            "response": content.strip(),
                            "sources_used": ["AI"],
                            "confidence": "Low",
                            "error": str(e)
                        })
                else:
                    logger.error(f"Unexpected DeepSeek API response format: {response_data}")
                    return json.dumps({
                        "response": "AI model did not return a valid response structure.",
                        "sources_used": [],
                        "confidence": "Low"
                    })
                
            except requests.exceptions.RequestException as req_err:
                last_error = req_err
                if attempt < DEEPSEEK_MAX_RETRIES - 1:
                    delay = DEEPSEEK_RETRY_DELAY * (attempt + 1)
                    logger.warning(f"API call failed (attempt {attempt + 1}/{DEEPSEEK_MAX_RETRIES}): {req_err} - retrying in {delay}s")
                    time.sleep(delay)
                    continue
                logger.error(f"Final API call failed after {DEEPSEEK_MAX_RETRIES} attempts: {req_err}")
                return f"AI service unavailable: {str(req_err)}"
            except Exception as api_err:
                logger.error(f"Error processing API response: {api_err}")
                return f"Error processing AI response: {str(api_err)}"
        
        return f"Failed to get AI response after {DEEPSEEK_MAX_RETRIES} attempts: {str(last_error)}"
        
    except Exception as e:
        logger.error(f"Error in ask_rag_question: {e}")
        return f"Error communicating with AI service: {str(e)}"

async def ask_genetic_question(prompt: str, pgs_data: List[Dict], pharmgkb_data: Optional[Dict] = None) -> Dict:
    """
    Specialized function for genetic questions with PGS/PharmGKB data
    
    Args:
        prompt: The genetic question
        pgs_data: List of PGS scores from genetics_analyzer
        pharmgkb_data: Optional PharmGKB drug-gene interactions
        
    Returns:
        Dict: Formatted response with risk analysis and recommendations
    """
    genetic_context = {
        "pgs_scores": pgs_data,
        "pharmgkb": pharmgkb_data or {}
    }
    
    try:
        response = await ask_rag_question(prompt, genetic_context)
        
        # Handle unified response format
        try:
            result = json.loads(response)
            
            # Handle empty PGS responses in Greek
            if "πολυγονιδιακά σκορ" in prompt and not result.get("pgs_scores_used"):
                result["response"] = "Δεν βρέθηκαν δεδομένα για πολυγονιδιακά σκορ (PGS) από το PGS Catalog στα διαθέσιμα έγγραφα του ασθενούς."
            
            # Handle empty PGS responses in Greek
            if "πολυγονιδιακά σκορ" in prompt and not result.get("pgs_scores_used"):
                result["response"] = "Δεν βρέθηκαν δεδομένα για πολυγονιδιακά σκορ (PGS) από το PGS Catalog στα διαθέσιμα έγγραφα του ασθενούς."
            
            return result
            
        except json.JSONDecodeError:
            # Create unified response format from plain text
            return {
                "response": response,
                "sources_used": ["AI"],
                "confidence": "Medium",
                "pgs_scores_used": [score.get('id') for score in pgs_data],
                "pharmgkb_used": bool(pharmgkb_data),
                "pubmed_used": "pubmed" in response.lower()
            }
            
    except Exception as e:
        logger.error(f"Genetic question failed: {e}")
        return {
            "error": str(e),
            "response": "Unable to process genetic question"
        }