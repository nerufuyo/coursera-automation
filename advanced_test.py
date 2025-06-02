#!/usr/bin/env python3
"""
Advanced AI Backend Testing
Tests the AI with more diverse and challenging questions
"""

import requests
import json
import time

def test_ai_backend():
    """Test the AI backend with advanced scenarios"""
    base_url = "http://localhost:8000"
    
    # Advanced test questions covering different domains
    advanced_questions = [
        {
            "question": "What is the fundamental concept of inheritance in object-oriented programming?",
            "options": [
                "Creating multiple copies of the same class",
                "A class can inherit properties and methods from another class", 
                "Classes cannot be modified after creation",
                "All methods must be public"
            ],
            "expected": "A class can inherit properties and methods from another class"
        },
        {
            "question": "In machine learning, what does 'overfitting' mean?",
            "options": [
                "The model performs too well on training data but poorly on new data",
                "The model uses too much memory",
                "The model trains too quickly",
                "The model has too few parameters"
            ],
            "expected": "The model performs too well on training data but poorly on new data"
        },
        {
            "question": "What is the primary purpose of a DNS server?",
            "options": [
                "To store website files",
                "To translate domain names to IP addresses",
                "To provide internet security",
                "To compress web pages"
            ],
            "expected": "To translate domain names to IP addresses"
        },
        {
            "question": "Which HTTP method is typically used to retrieve data from a server?",
            "options": [
                "POST",
                "PUT", 
                "GET",
                "DELETE"
            ],
            "expected": "GET"
        },
        {
            "question": "What is the correct formula for calculating the area of a circle?",
            "options": [
                "2πr",
                "πr²",
                "πd",
                "2πr²"
            ],
            "expected": "πr²"
        },
        {
            "question": "In databases, what does ACID stand for?",
            "options": [
                "Atomicity, Consistency, Isolation, Durability",
                "Advanced Computer Information Database",
                "Automatic Calculated Index Data",
                "Application Control Interface Design"
            ],
            "expected": "Atomicity, Consistency, Isolation, Durability"
        },
        {
            "question": "Which of the following is NOT a valid Python data type?",
            "options": [
                "list",
                "tuple",
                "array",
                "dictionary"
            ],
            "expected": "array"
        },
        {
            "question": "What is the time complexity of binary search?",
            "options": [
                "O(n)",
                "O(n²)",
                "O(log n)",
                "O(1)"
            ],
            "expected": "O(log n)"
        }
    ]
    
    print("🧪 Advanced AI Backend Testing")
    print("=" * 60)
    
    correct_answers = 0
    total_questions = len(advanced_questions)
    
    for i, q in enumerate(advanced_questions, 1):
        print(f"\n📝 Question {i}: {q['question']}")
        print("Options:")
        for j, option in enumerate(q['options'], 1):
            print(f"  {j}. {option}")
        
        # Make API request
        try:
            response = requests.post(
                f"{base_url}/answer",
                json={
                    "question": q["question"],
                    "options": q["options"],
                    "type": "multiple-choice"
                },
                timeout=10
            )
            
            if response.status_code == 200:
                result = response.json()
                print(f"🤖 AI Answer: {result['answer']}")
                print(f"📊 Confidence: {result['confidence']:.2f}")
                print(f"🔍 Source: {result['source']}")
                if result.get('reasoning'):
                    print(f"💭 Reasoning: {result['reasoning'][:100]}...")
                
                print(f"✅ Expected: {q['expected']}")
                
                if result['answer'] == q['expected']:
                    print("✅ CORRECT!")
                    correct_answers += 1
                else:
                    print("❌ INCORRECT")
            else:
                print(f"❌ API Error: {response.status_code}")
                
        except Exception as e:
            print(f"❌ Request failed: {e}")
        
        time.sleep(0.5)  # Rate limiting
    
    print("\n" + "=" * 60)
    print(f"📊 Final Results: {correct_answers}/{total_questions} correct")
    print(f"🎯 Accuracy: {(correct_answers/total_questions)*100:.1f}%")
    
    if correct_answers / total_questions >= 0.8:
        print("🎉 Excellent performance!")
    elif correct_answers / total_questions >= 0.6:
        print("👍 Good performance!")
    else:
        print("⚠️ Performance needs improvement")

def test_batch_processing():
    """Test batch processing functionality"""
    print("\n🔄 Testing Batch Processing")
    print("-" * 40)
    
    batch_questions = [
        {
            "question": "What is 2 + 2?",
            "options": ["3", "4", "5", "6"],
            "type": "multiple-choice"
        },
        {
            "question": "What is the capital of Italy?",
            "options": ["Rome", "Milan", "Venice", "Naples"],
            "type": "multiple-choice"
        }
    ]
    
    try:
        response = requests.post(
            "http://localhost:8000/batch-answer",
            json=batch_questions,
            timeout=15
        )
        
        if response.status_code == 200:
            results = response.json()["results"]
            print(f"✅ Batch processed {len(results)} questions")
            for i, result in enumerate(results):
                print(f"  Question {i+1}: {result['answer']} (confidence: {result['confidence']:.2f})")
        else:
            print(f"❌ Batch API Error: {response.status_code}")
            
    except Exception as e:
        print(f"❌ Batch request failed: {e}")

if __name__ == "__main__":
    print("Starting advanced AI backend test...")
    
    # Check if server is running
    try:
        print("Checking server health...")
        health_response = requests.get("http://localhost:8000/health", timeout=5)
        print(f"Health check status: {health_response.status_code}")
        if health_response.status_code == 200:
            print("✅ AI Backend server is running")
            test_ai_backend()
            test_batch_processing()
        else:
            print("❌ AI Backend server health check failed")
    except Exception as e:
        print(f"❌ Cannot connect to AI Backend server: {e}")
        print("🔧 Make sure to run: python ai_backend.py")
