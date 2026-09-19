# main.py
from data import MOCK_INCIDENTS, MOCK_RESOURCES
from engine import process_module_4

if __name__ == "__main__":
    output = process_module_4(MOCK_INCIDENTS, MOCK_RESOURCES)
    print("Module 4 Output Package (allocation_inputs):\n")
    print(output)