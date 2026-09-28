import sys
import os
sys.path.append(os.path.dirname(__file__))

from app.agents.requirement_agent import RequirementAgent

def run_test():
    print("=== Phase 4: Requirement Agent Test ===")
    request = input("Enter a customer request: ")
    
    agent = RequirementAgent()
    try:
        reqs = agent.extract_requirements(request)
        print("\nRAW REQUEST")
        print(request)
        print("\nSTRUCTURED REQUIREMENTS")
        print(reqs.model_dump_json(indent=2))
    except Exception as e:
        print(f"\nError: {e}")

if __name__ == "__main__":
    run_test()
