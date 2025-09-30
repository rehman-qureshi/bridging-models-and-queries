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

1. **Run the main driver script with a PNML model file:**

    ```bash
    python driver.py <path_to_pnml_file> <TRUE|FALSE>
    ```
    **Example:**
    ```bash
    python .\driver.py .\BPIC19-Model.pnml TRUE
    ```
    - The last argument (TRUE or FALSE) specifies whether to skip silent transitions during matrix processing.
2. **Matrix Manipulation:**
    - Use create_alpha_relations_matrix.py to generate and process the activity relations matrix.
    - Silent transitions are handled and resolved to propagate relations to actual activities before removal.

3. **Relaxation Operations for BPIC19 Model:**
    - Relaxation operations for the BPIC19 model are defined in relaxation-operations.json.
    - You can interactively manipulate the matrix and apply relaxations.
    
4. **Conformance Checking:**
    - Use determine_conformance_rate.py to calculate conformance rates and parse declarative constraints.
    - Outputs such as conformance rate, affected trace count, and conforming trace count are printed to the console.
### Features

- **Matrix Manipulation:** Interactive editing and relaxation of activity relationships.
- **Constraint Generation:** Automatic extraction of declarative constraints (e.g., ChainResponse, AlternateResponse).
- **Conformance Checking:** Integration with PM4Py for process mining and conformance rate calculation.
- **Silent Transition Handling:** Transitive closure and propagation of relations through silent transitions.

### Output

- Declarative constraints in readable format.
- Conformance rate and trace statistics are printed to the console.

---

For more details, see the code comments and function docstrings.