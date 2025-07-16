#!/usr/bin/env python3
"""
Test LLM's math capabilities with random arithmetic problems.

This script tests if the LLM can correctly solve basic arithmetic problems
using the calculator tool.
"""

import asyncio
import random
import re
from typing import Dict, List, Tuple, Optional

# Add parent directory to path
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from llmchat import LLMChat, console

class MathTest:
    def __init__(self, model: str = "phi3"):
        self.chat = LLMChat(model=model)
        self.correct = 0
        self.total = 0
        
    def generate_math_problem(self) -> Tuple[str, float]:
        """Generate a random arithmetic problem and its solution."""
        # Generate random numbers and operator
        num1 = random.randint(1, 100)
        num2 = random.randint(1, 100)
        operator = random.choice(['+', '-', '*', '/'])
        
        # Ensure division results in whole numbers for simplicity
        if operator == '/':
            num1 = num1 * num2
            
        # Calculate the correct answer
        expression = f"{num1} {operator} {num2}"
        try:
            correct_answer = eval(expression)
            # Round to 2 decimal places to avoid floating point precision issues
            correct_answer = round(correct_answer, 2)
            return f"What is {expression}?", correct_answer
        except Exception as e:
            # If there's an error (shouldn't happen with our constraints), try again
            return self.generate_math_problem()
    
    def extract_number(self, text: str) -> Optional[float]:
        """Extract the first number found in the text."""
        # Look for numbers in the text, including decimals and negative numbers
        matches = re.findall(r'-?\d+\.?\d*', text.replace(',', ''))
        if matches:
            try:
                return float(matches[0])
            except (ValueError, IndexError):
                pass
        return None
    
    async def run_test(self, num_problems: int = 5):
        """Run the math test with the specified number of problems."""
        console.print(f"\n{'='*50}")
        console.print(f"Starting Math Test with {num_problems} problems")
        console.print(f"Using model: {self.chat.model}")
        console.print(f"{'='*50}\n")
        
        for i in range(1, num_problems + 1):
            # Generate a problem
            problem, correct_answer = self.generate_math_problem()
            console.print(f"\n[bold]Problem {i}/{num_problems}[/] {problem}")
            
            try:
                # Get the LLM's response
                response = await self.chat.chat_completion(problem)
                console.print(f"[assistant]Assistant:[/] {response}")
                
                # Extract the answer
                llm_answer = self.extract_number(response)
                
                if llm_answer is not None:
                    # Compare the answers (with a small tolerance for floating point)
                    if abs(llm_answer - correct_answer) < 0.01:
                        console.print(f"[success]✅ Correct! {problem} = {correct_answer}[/]")
                        self.correct += 1
                    else:
                        console.print(f"[danger]❌ Incorrect. {problem} = {correct_answer} (Got: {llm_answer})[/]")
                else:
                    console.print(f"[warning]❓ Could not extract answer from response[/]")
                    console.print(f"[info]   Expected: {correct_answer}[/]")
                
                self.total += 1
                
            except Exception as e:
                console.print(f"[danger]⚠️ Error: {str(e)}[/]")
            
            # Small delay to avoid rate limiting
            await asyncio.sleep(1)
        
        # Print summary
        accuracy = (self.correct / self.total * 100) if self.total > 0 else 0
        console.print(f"\n{'='*50}")
        console.print(f"[bold]Test Complete![/]")
        console.print(f"Correct: {self.correct}/{self.total}")
        console.print(f"Accuracy: {accuracy:.1f}%")
        console.print(f"{'='*50}\n")

async def main():
    """Run the math test."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Test LLM math capabilities')
    parser.add_argument('--model', type=str, default='phi3',
                       help='Model to use (default: phi3 - fast 3.8B model)')
    # Note: Make sure you've run 'ollama pull phi3' first
    parser.add_argument('--problems', type=int, default=5,
                       help='Number of problems to test (default: 5)')
    
    args = parser.parse_args()
    
    # Run the test
    tester = MathTest(model=args.model)
    await tester.run_test(num_problems=args.problems)

if __name__ == "__main__":
    asyncio.run(main())
