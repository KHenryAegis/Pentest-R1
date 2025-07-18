from agent import PentestAgent, PentestExecutor

def main():
    MODEL_CONFIG = {
        'type': 'openai',
        'name': 'pentest-r1',
        'base_url': '',
        'api_key': 'EMPTY'
    }

    TEST_SCENARIOS = [
    {
          "level": "in-vitro",
          "category": "access_control",
         "epochs": 30,
         "iterations": 5
      },
     {
         "level": "in-vitro",
         "category": "cryptography",
         "epochs": 30,
         "iterations": 4
      },
      {
          "level": "in-vitro",
          "category": "web_security",
          "epochs": 30,
          "iterations": 7
      },
      {
        "level": "real-world",
        "category": "cve",
        "epochs": 30,
        "iterations": 11
    },
     {
        "level": "in-vitro",
        "category": "network_security",
        "epochs": 30,
        "iterations": 6
    }
]

    agent = PentestAgent(MODEL_CONFIG)
    executor = PentestExecutor(agent)

    total_success = 0
    total_tests = 0
    for scenario in TEST_SCENARIOS:
        print(f"Running {scenario['category']} scenario...")
        success_count, iterations = executor.run_scenario(scenario)
        total_success += success_count
        total_tests += iterations

    completion_rate = (total_success / total_tests) * 100 if total_tests > 0 else 0
    print(f"Overall task completion rate: {completion_rate:.2f}%")
    
if __name__ == "__main__":
    main()
    
