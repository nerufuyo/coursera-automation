#!/usr/bin/env python3
"""
Coursera Automation AI Backend
Provides intelligent question answering for Coursera quizzes
"""

import asyncio
import json
import logging
import re
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from datetime import datetime

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
import uvicorn

# Optional AI libraries - install as needed
try:
    import openai
    HAS_OPENAI = True
except ImportError:
    HAS_OPENAI = False

try:
    from transformers import pipeline
    HAS_TRANSFORMERS = True
except ImportError:
    HAS_TRANSFORMERS = False

try:
    import requests
    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Coursera Automation AI", version="1.0.0")

# Enable CORS for browser extension
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Pydantic models
class QuestionRequest(BaseModel):
    question: str
    options: List[str]
    type: str = "multiple-choice"
    context: Optional[str] = None

class AnswerResponse(BaseModel):
    answer: str
    confidence: float
    reasoning: Optional[str] = None
    source: str

@dataclass
class AIProvider:
    name: str
    enabled: bool
    priority: int

class CourseraAI:
    def __init__(self):
        self.providers = [
            AIProvider("openai", HAS_OPENAI, 1),
            AIProvider("transformers", HAS_TRANSFORMERS, 2),
            AIProvider("heuristic", True, 3)
        ]
        
        # Initialize AI models
        self.qa_pipeline = None
        if HAS_TRANSFORMERS:
            try:
                self.qa_pipeline = pipeline("question-answering", 
                                           model="distilbert-base-cased-distilled-squad")
                logger.info("Loaded Transformers QA model")
            except Exception as e:
                logger.warning(f"Failed to load Transformers model: {e}")
        
        # OpenAI setup (if available)
        self.openai_client = None
        if HAS_OPENAI:
            # You'll need to set your OpenAI API key
            # openai.api_key = "your-api-key-here"
            pass
    
    async def answer_question(self, question: str, options: List[str], 
                            question_type: str = "multiple-choice", 
                            context: str = None) -> Dict[str, Any]:
        """
        Answer a question using the best available AI provider
        """
        for provider in sorted(self.providers, key=lambda x: x.priority):
            if not provider.enabled:
                continue
            
            try:
                if provider.name == "openai" and self.openai_client:
                    return await self._answer_with_openai(question, options, question_type, context)
                elif provider.name == "transformers" and self.qa_pipeline:
                    return await self._answer_with_transformers(question, options, question_type, context)
                elif provider.name == "heuristic":
                    return await self._answer_with_heuristics(question, options, question_type, context)
            except Exception as e:
                logger.error(f"Error with {provider.name}: {e}")
                continue
        
        # Fallback
        return {
            "answer": options[0] if options else "",
            "confidence": 0.1,
            "reasoning": "Fallback answer - no AI providers available",
            "source": "fallback"
        }
    
    async def _answer_with_openai(self, question: str, options: List[str], 
                                question_type: str, context: str) -> Dict[str, Any]:
        """Answer using OpenAI GPT models"""
        prompt = self._create_prompt(question, options, question_type, context)
        
        try:
            # This is a placeholder - you'll need to implement with your OpenAI setup
            # response = await openai.ChatCompletion.acreate(
            #     model="gpt-3.5-turbo",
            #     messages=[{"role": "user", "content": prompt}],
            #     temperature=0.1
            # )
            # answer = response.choices[0].message.content.strip()
            
            # For now, fall back to heuristics
            return await self._answer_with_heuristics(question, options, question_type, context)
            
        except Exception as e:
            logger.error(f"OpenAI error: {e}")
            raise
    
    async def _answer_with_transformers(self, question: str, options: List[str], 
                                      question_type: str, context: str) -> Dict[str, Any]:
        """Answer using Hugging Face Transformers"""
        if not self.qa_pipeline:
            raise Exception("Transformers pipeline not available")
        
        best_answer = None
        best_score = 0
        reasoning = []
        
        # Create context from question and options
        full_context = f"Question: {question}\n"
        if context:
            full_context += f"Context: {context}\n"
        full_context += "Options:\n" + "\n".join([f"- {opt}" for opt in options])
        
        # Try each option as a potential answer
        for option in options:
            try:
                # Ask "Which option is correct?" with the context
                result = self.qa_pipeline(
                    question=f"Which option is the correct answer: {option}?",
                    context=full_context
                )
                
                score = result['score']
                reasoning.append(f"{option}: {score:.3f}")
                
                if score > best_score:
                    best_score = score
                    best_answer = option
                    
            except Exception as e:
                logger.warning(f"Error processing option '{option}': {e}")
        
        if not best_answer:
            best_answer = options[0]
            best_score = 0.1
        
        return {
            "answer": best_answer,
            "confidence": min(best_score * 2, 1.0),  # Scale score
            "reasoning": "; ".join(reasoning),
            "source": "transformers"
        }
    
    async def _answer_with_heuristics(self, question: str, options: List[str], 
                                    question_type: str, context: str) -> Dict[str, Any]:
        """Answer using enhanced rule-based heuristics"""
        question_lower = question.lower()
        reasoning = []
        
        # Enhanced knowledge base for common questions
        knowledge_patterns = {
            # Geography and capitals
            'capital.*france': 'paris',
            'capital.*uk|united kingdom': 'london',
            'capital.*germany': 'berlin',
            'capital.*italy': 'rome',
            'capital.*spain': 'madrid',
            'capital.*japan': 'tokyo',
            'capital.*china': 'beijing',
            'capital.*russia': 'moscow',
            
            # Programming and technology
            'machine learning.*language|language.*machine.*learning|programming.*language.*known.*machine': 'python',
            'python.*machine.*learning|python.*known.*for': 'python',
            'html.*stand': 'hypertext markup language',
            'css.*stand': 'cascading style sheets',
            'object.*oriented.*programming': 'classes and objects',
            'javascript.*browser|javascript.*used.*for': 'javascript',
            'sql.*database|sql.*stands': 'structured query language',
            'api.*stands.*for': 'application programming interface',
            'json.*stands.*for': 'javascript object notation',
            'xml.*stands.*for': 'extensible markup language',
            'http.*retrieve|http.*protocol': 'get',
            'version control.*git': 'track changes',
            'tcp.*ip|transmission.*control': 'transmission control protocol',
            'dns.*stands|domain.*name.*system': 'domain name system',
            'url.*stands|uniform.*resource': 'uniform resource locator',
            
            # Computer Science concepts
            'algorithm.*complexity|big.*o.*notation': 'big o',
            'binary.*search.*complexity|time.*complexity.*binary': 'o(log n)',
            'database.*acid': 'atomicity',
            'inheritance.*programming|inherit.*properties.*methods': 'inherit',
            'polymorphism.*programming': 'polymorphism',
            'encapsulation.*programming': 'encapsulation',
            'overfitting.*machine.*learning|model.*performs.*too.*well': 'training data',
            'overfitting.*means|overfitting.*definition': 'performs too well on training',
            'dns.*server|dns.*purpose': 'translate domain names',
            'http.*retrieve|http.*get': 'get',
            
            # Mathematics and formulas
            'area.*circle|circle.*area': 'πr²',
            'circumference.*circle': '2πr',
            'pythagorean.*theorem': 'a² + b² = c²',
            'pi.*value|value.*pi': '3.14159',
            'fibonacci.*sequence': '0, 1, 1, 2, 3, 5, 8',
            
            # Python specific
            'python.*data.*type|valid.*python.*type': 'list|tuple|dict',
            'not.*valid.*python|invalid.*python': 'array',
            
            # Science and math
            'speed.*light': '299,792,458',
            'gravity.*earth': '9.8',
            'photosynthesis.*produces': 'oxygen',
            'mitochondria.*powerhouse': 'cell',
            'dna.*stands.*for': 'deoxyribonucleic acid',
            'rna.*stands.*for': 'ribonucleic acid',
            
            # Business and economics
            'gdp.*stands.*for': 'gross domestic product',
            'ceo.*stands.*for': 'chief executive officer',
            'roi.*stands.*for': 'return on investment'
        }
        
        # Rule 1: Knowledge-based matching with negative question handling
        knowledge_scores = {}
        is_negative_question = any(neg in question_lower for neg in ['not', 'incorrect', 'false', 'except', 'excluding'])
        
        for i, option in enumerate(options):
            option_lower = option.lower()
            score = 0
            
            for pattern, expected in knowledge_patterns.items():
                if re.search(pattern, question_lower):
                    if expected.lower() in option_lower:
                        if is_negative_question:
                            # For negative questions, penalize matches (we want the opposite)
                            score -= 2
                            reasoning.append(f"Negative question: penalizing '{option}' for pattern '{pattern}'")
                        else:
                            score += 3
                            reasoning.append(f"Knowledge match: '{option}' matches pattern for '{pattern}'")
                        break
            
            # Special handling for negative questions about Python data types
            if 'not.*valid.*python' in question_lower or 'invalid.*python' in question_lower:
                if option_lower in ['array', 'pointer', 'char', 'int', 'float']:
                    score += 3  # Increased score for likely invalid types
                    reasoning.append(f"Negative Python type question: '{option}' is likely not a valid Python type")
                elif option_lower in ['list', 'tuple', 'dict', 'dictionary', 'set', 'str', 'string']:
                    score -= 1  # Penalize valid Python types in negative questions
                    reasoning.append(f"Negative Python type question: '{option}' is a valid Python type")
            
            knowledge_scores[i] = score
        
        # Rule 2: Keyword analysis
        keyword_scores = {}
        positive_keywords = [
            'correct', 'true', 'yes', 'always', 'all', 'both', 'every',
            'most', 'best', 'should', 'must', 'important', 'necessary',
            'primarily', 'main', 'key', 'essential', 'fundamental'
        ]
        
        negative_keywords = [
            'incorrect', 'false', 'no', 'never', 'none', 'neither', 'wrong',
            'not', 'least', 'worst', 'avoid', 'don\'t', 'cannot', 'impossible'
        ]
        
        for i, option in enumerate(options):
            option_lower = option.lower()
            score = 0
            
            # Check for positive indicators
            for keyword in positive_keywords:
                if keyword in option_lower:
                    score += 0.5
                    reasoning.append(f"Positive keyword '{keyword}' in option {i+1}")
            
            # Check for negative patterns
            question_negative = any(neg in question_lower for neg in negative_keywords)
            option_negative = any(neg in option_lower for neg in negative_keywords)
            
            if question_negative and option_negative:
                score += 0.3  # Double negative often correct
            elif not question_negative and not option_negative:
                score += 0.2  # Both positive
            
            keyword_scores[i] = score
        
        # Rule 3: Length and complexity heuristic
        length_scores = {}
        max_length = max(len(opt) for opt in options) if options else 1
        for i, option in enumerate(options):
            # Moderate length often better than too short or too long
            length_ratio = len(option) / max_length
            if 0.3 <= length_ratio <= 0.8:
                length_scores[i] = 0.5
            elif length_ratio > 0.8:
                length_scores[i] = 0.3  # Longest option bonus
            else:
                length_scores[i] = 0.1
        
        # Rule 4: Academic and technical patterns
        academic_scores = {}
        academic_patterns = [
            'according to', 'research shows', 'studies indicate',
            'analysis reveals', 'theory suggests', 'methodology',
            'framework', 'paradigm', 'concept', 'principle'
        ]
        
        technical_patterns = [
            'algorithm', 'protocol', 'specification', 'standard',
            'implementation', 'architecture', 'structure', 'design'
        ]
        
        for i, option in enumerate(options):
            option_lower = option.lower()
            score = 0
            
            for pattern in academic_patterns:
                if pattern in option_lower:
                    score += 0.3
            
            for pattern in technical_patterns:
                if pattern in option_lower:
                    score += 0.2
            
            # Look for explanatory words
            explanatory_words = ['because', 'therefore', 'however', 'although', 'since', 'while']
            for word in explanatory_words:
                if word in option_lower:
                    score += 0.1
            
            academic_scores[i] = score
        
        # Rule 5: Specific question type analysis
        question_type_scores = {}
        for i, option in enumerate(options):
            option_lower = option.lower()
            score = 0
            
            # True/False questions
            if any(word in question_lower for word in ['true', 'false', 'correct', 'incorrect']):
                if 'true' in option_lower or 'correct' in option_lower:
                    score += 0.4
            
            # Definition questions
            if any(word in question_lower for word in ['define', 'definition', 'means', 'refers to']):
                if len(option) > 30:  # Definitions tend to be longer
                    score += 0.3
            
            # Best practice questions
            if any(word in question_lower for word in ['best', 'recommended', 'should', 'practice']):
                if any(word in option_lower for word in ['best', 'recommended', 'should', 'proper']):
                    score += 0.5
            
            question_type_scores[i] = score
        
        # Combine all scores with weights
        final_scores = {}
        for i in range(len(options)):
            final_scores[i] = (
                knowledge_scores.get(i, 0) * 0.4 +      # Highest weight for knowledge
                keyword_scores.get(i, 0) * 0.25 +       # Keyword analysis
                length_scores.get(i, 0) * 0.15 +        # Length heuristic
                academic_scores.get(i, 0) * 0.1 +       # Academic patterns
                question_type_scores.get(i, 0) * 0.1    # Question type specific
            )
        
        # Find best option
        if final_scores:
            best_idx = max(final_scores.keys(), key=lambda k: final_scores[k])
            best_answer = options[best_idx]
            max_score = final_scores[best_idx]
            confidence = min(max_score / 2, 0.95)  # Scale confidence
            
            # Boost confidence if we had a knowledge match
            if knowledge_scores.get(best_idx, 0) > 0:
                confidence = min(confidence + 0.3, 0.95)
                
        else:
            best_answer = options[0] if options else ""
            confidence = 0.1
        
        # Add scoring breakdown to reasoning
        reasoning.append(f"Scores: {[f'{i+1}:{final_scores.get(i, 0):.2f}' for i in range(len(options))]}")
        
        return {
            "answer": best_answer,
            "confidence": confidence,
            "reasoning": "; ".join(reasoning),
            "source": "enhanced_heuristic"
        }
    
    def _create_prompt(self, question: str, options: List[str], 
                      question_type: str, context: str) -> str:
        """Create a prompt for AI models"""
        prompt = f"""You are an expert academic assistant helping with online course questions.

Question: {question}

Options:
"""
        for i, option in enumerate(options, 1):
            prompt += f"{i}. {option}\n"
        
        if context:
            prompt += f"\nContext: {context}\n"
        
        prompt += f"""
Please select the most correct answer and provide your reasoning.
Type: {question_type}

Answer with just the text of the correct option."""
        
        return prompt

# Global AI instance
coursera_ai = CourseraAI()

@app.get("/")
async def root():
    return {"message": "Coursera Automation AI Backend", "status": "running"}

@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "providers": [
            {"name": p.name, "enabled": p.enabled, "priority": p.priority} 
            for p in coursera_ai.providers
        ]
    }

@app.post("/answer", response_model=AnswerResponse)
async def answer_question(request: QuestionRequest):
    """Answer a Coursera question"""
    try:
        if not request.question.strip():
            raise HTTPException(status_code=400, detail="Question cannot be empty")
        
        if not request.options:
            raise HTTPException(status_code=400, detail="Options cannot be empty")
        
        logger.info(f"Answering question: {request.question[:100]}...")
        
        result = await coursera_ai.answer_question(
            question=request.question,
            options=request.options,
            question_type=request.type,
            context=request.context
        )
        
        logger.info(f"Answer: {result['answer']} (confidence: {result['confidence']:.3f})")
        
        return AnswerResponse(
            answer=result["answer"],
            confidence=result["confidence"],
            reasoning=result.get("reasoning"),
            source=result["source"]
        )
        
    except Exception as e:
        logger.error(f"Error answering question: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/batch-answer")
async def batch_answer_questions(requests: List[QuestionRequest]):
    """Answer multiple questions in batch"""
    results = []
    
    for request in requests:
        try:
            result = await coursera_ai.answer_question(
                question=request.question,
                options=request.options,
                question_type=request.type,
                context=request.context
            )
            results.append(result)
        except Exception as e:
            logger.error(f"Error in batch question: {e}")
            results.append({
                "answer": request.options[0] if request.options else "",
                "confidence": 0.1,
                "reasoning": f"Error: {str(e)}",
                "source": "error"
            })
    
    return {"results": results}

if __name__ == "__main__":
    logger.info("Starting Coursera Automation AI Backend...")
    logger.info(f"OpenAI available: {HAS_OPENAI}")
    logger.info(f"Transformers available: {HAS_TRANSFORMERS}")
    logger.info(f"Requests available: {HAS_REQUESTS}")
    
    uvicorn.run(
        "ai_backend:app",
        host="127.0.0.1",
        port=8000,
        reload=True,
        log_level="info"
    )
