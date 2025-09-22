# Bridging Imperative Process Models and Process Data Queries—Translation and Relaxation

This repository provides a Python command-line tool for interactively manipulating a matrix representation of activities and their relationships. The tool supports a variety of relaxation and transformation operations on the activity matrix, and can generate declarative constraints for process mining and conformance checking.

## Getting Started

### Prerequisites

- Python 3.x
- pandas
- pm4py
- Require [BPIC19_3way_IbeforeGR_standardPO_complete.xes](https://icpmconference.org/2019/icpm-2019/contests-challenges/bpi-challenge-2019/) file in the current folder

### Installation

Install the required Python packages:

```bash
pip install pandas pm4py
```

### Usage

1. **Run the main script with a txt file:**

    ```bash
    python refactored.py <path_to_txt_file>
    ```
    **Example:**
    ```bash
    python .\refactored.py .\BPIC19-Matrix.txt
    ```

2. **Relaxation Operations for BPIC19 Model:**
    - The details of relaxation operations are given in relaxation-operations.json file
    

### Features

- **Matrix Manipulation:** Interactive editing and relaxation of activity relationships.
- **Constraint Generation:** Automatic extraction of declarative constraints (e.g., ChainResponse, AlternateResponse).
- **Conformance Checking:** Integration with PM4Py for process mining and conformance rate calculation.

### Example Data Format

The input text file should define activities and their relationships as Python lists:

```python
activities = ['CPRI','CPOI','ROC','CP','CQ','RGR','RIR','VCI','RPB','CI']
data = [
    ['-','→', '-', '-', '-', '-', '-', '-', '-', '-'],
    ['←', '-', '→', '→', '→', '→', '→', '→', '-', '-'],
    ['-', '←', '-', '-', '→', '→', '→', '→', '-', '-'],
    # ... more rows ...
]
```

### Output

- Declarative constraints in readable format.
- Conformance Rate

---

For more details, see the code comments and function docstrings.