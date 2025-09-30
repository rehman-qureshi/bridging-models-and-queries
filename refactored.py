from collections import namedtuple
import pandas as pd
import sys
import ast
import os
import json
from determine_conformance_rate import determine_conformance_rate_function


# Define the structure for the declarative constraints for clarity
ChainResponse = namedtuple('ChainResponse', ['antecedent', 'consequent'])
AlternateResponse = namedtuple('AlternateResponse', ['antecedent', 'consequent'])
AlternateResponse_P = namedtuple('AlternateResponse_P', ['antecedent', 'consequent']) # Dedicated AlternateResponse for parallel activities

def parse_relation_matrix(df):
    """
    Parses a DataFrame of behavioral relations into D and E sets.
    Handles '→', '←', '≺', '≻', and '||' symbols.
    """
    D = set()
    E = set()
    
    for row_label, row in df.iterrows():
        for col_label, symbol in row.items():
            if symbol == '→':
                D.add((row_label, col_label))
            elif symbol == '←':
                D.add((col_label, row_label))
            elif symbol == '≺':
                E.add((row_label, col_label))
            elif symbol == '≻':
                E.add((col_label, row_label))
            elif symbol == '||':
                # Concurrency implies a bi-directional directly-follows relationship
                D.add((row_label, col_label))
                D.add((col_label, row_label))
            elif symbol == '≺≻':
                # if we have bi-directional eventually-follows relationship
                E.add((row_label, col_label))
                E.add((col_label, row_label))
    return D, E

def update_matrix_with_tc(df: pd.DataFrame, E: set) -> pd.DataFrame:
    """
    Updates a matrix DataFrame with symbols from the transitive closure set.

    - Updates cell (a, b) to '≺' and (b, a) to '≻' if (a, b) is in E.
    - Updates cell (a, b) and (b, a) to '≺≻' if both (a, b) and (b, a) are in E.
    - Does not overwrite existing strong relations ('→', '←', '||').

    Args:
        df (pd.DataFrame): The original matrix.
        E (set): The computed transitive closure (eventually-follows) set.

    Returns:
        pd.DataFrame: A new DataFrame with the updated symbols.
    """
    updated_df = df.copy()
    processed_pairs = set()
    strong_symbols = {'→', '←', '||'}

    for a, b in E:
        if (a, b) in processed_pairs:
            continue

        is_forward = (a, b) in E
        is_backward = (b, a) in E

        if is_forward and is_backward and a != b:
            # Handle bidirectional case: '≺≻'
            if updated_df.loc[a, b] not in strong_symbols:
                updated_df.loc[a, b] = '≺≻'
            if updated_df.loc[b, a] not in strong_symbols:
                updated_df.loc[b, a] = '≺≻'
            processed_pairs.add((a, b))
            processed_pairs.add((b, a))
        elif is_forward and a != b:
            # Handle one-way case: '≺' and '≻'
            if updated_df.loc[a, b] not in strong_symbols:
                updated_df.loc[a, b] = '≺'
            if updated_df.loc[b, a] not in strong_symbols:
                updated_df.loc[b, a] = '≻'
            processed_pairs.add((a, b))

    return updated_df


def compute_transitive_closure(D):
    """
    Computes the transitive closure of the directly-follows relation D.
    """
    adj = {}
    nodes = set()
    for a, b in D:
        if a not in adj:
            adj[a] = set()
        adj[a].add(b)
        nodes.add(a)
        nodes.add(b)

    transitive_closure_set = set()
    for start_node in nodes:
        to_visit = list(adj.get(start_node, []))
        visited = set(to_visit)
        while to_visit:
            current_node = to_visit.pop()
            #if current_node != start_node:
            transitive_closure_set.add((start_node, current_node))
            for neighbor in adj.get(current_node, []):
                if neighbor not in visited:
                    visited.add(neighbor)
                    to_visit.append(neighbor)
    return transitive_closure_set


def is_optional_activity(x, D):
    """
    Checks if an activity x is optional based on a bypass pattern.

    An activity is optional if for every valid direct predecessor 'a' and
    successor 'b' of 'x', a direct bypass from 'a' to 'b' exists.

    Args:
        x (any): The activity to check.
        D (set): A set of tuples representing directly-follows relations.

    Returns:
        bool: True if the activity is considered optional, False otherwise.
    """
    predecessors = {a for a, target in D if target == x}
    successors = {b for source, b in D if source == x}

    # An activity needs at least one predecessor and one successor to be bypassed.
    if not predecessors or not successors:
        return False

    # Track if we find at least one valid path to check for a bypass.
    found_valid_path_to_check = False

    for a in predecessors:
        for b in successors:
            # A path (a, x, b) is valid for checking if 'a' and 'b' are not
            # in a parallel relation with 'x' or each other.
            is_parallel = (x, a) in D or (b, x) in D or (b, a) in D
            if not is_parallel:
                found_valid_path_to_check = True
                # If a valid path does not have a direct bypass (a, b),
                # then 'x' cannot be considered optional.
                if (a, b) not in D:
                    return False

    # The activity is optional only if at least one valid path was found
    # and all such paths had a bypass. If no such paths were found, it's not
    # considered optional by this specific definition.
    return found_valid_path_to_check


def generate_binary_constraints(D, E, TC_D):
    """
    Generates a set of declarative binary constraints based on directly-follows (D)
    and eventually-follows (E) relations, using the detailed IsOptionalActivity logic.

    Args:
        D (set): A set of tuples (a, b) representing that activity b directly follows a.
        E (set): A set of tuples (a, b) representing that activity b eventually follows a.
        TC_D (set): The transitive closure of the directly-follows relation D.
    Returns:
        set: A set of declarative constraints (ChainResponse and AlternateResponse).
    """
    C = set()
    A_D = {a for a, b in D}

    for a in A_D:
        S = {x for source, x in D if source == a}
        C.add(ChainResponse(antecedent=frozenset({a}), consequent=frozenset(S)))

        s_list = list(S)
        for i in range(len(s_list)):
            for j in range(i + 1, len(s_list)):
                b, c = s_list[i], s_list[j]
                if (b, c) in D and (c, b) in D:
                    # The algorithm adds a constraint if the activity is NOT optional.
                    if not is_optional_activity(b, D) and (b,a) not in D:
                        C.add(AlternateResponse_P(antecedent=frozenset({a}), consequent=frozenset({b})))
                    if not is_optional_activity(c, D) and (c,a) not in D:
                        C.add(AlternateResponse_P(antecedent=frozenset({a}), consequent=frozenset({c})))
        
    A_E = {a for a, b in E}
    for a in A_E:
        S = {x for source, x in E if source == a and (source, x) not in TC_D}
        if S:
            C.add(AlternateResponse(antecedent=frozenset({a}), consequent=frozenset(S)))

    return C


# --- Relaxation Logic ---

def relax_remove_activity(df: pd.DataFrame, activity: str) -> pd.DataFrame:
    """
    Makes an activity optional and allows it to appear anywhere by setting
    all its relationships with other activities to '≺≻'.
    """
    df_relaxed = df.copy()
    if activity in df_relaxed.index:
        for other_activity in df_relaxed.index:
            if activity != other_activity:
                df_relaxed.loc[activity, other_activity] = '≺≻'
                df_relaxed.loc[other_activity, activity] = '≺≻'
    return df_relaxed

def relax_remove_all_relationships(df: pd.DataFrame, act1: str, act2: str) -> pd.DataFrame:
    """
    Makes two activities independent by setting their relationship to '≺≻'.
    """
    df_relaxed = df.copy()
    df_relaxed.loc[act1, act2] = '≺≻'
    df_relaxed.loc[act2, act1] = '≺≻'
    return df_relaxed

def relax_exclusive_to_direct(df: pd.DataFrame, source: str, target: str) -> pd.DataFrame:
    """
    Turns a non-existent relation ('-') into a direct one ('→' and '←').
    """
    df_relaxed = df.copy()
    if source == target and df_relaxed.loc[source, target] == '-':
        df_relaxed.loc[source, target] = '||'
        df_relaxed.loc[target, source] = '||'
    elif df_relaxed.loc[source, target] == '-':
        df_relaxed.loc[source, target] = '→'
        df_relaxed.loc[target, source] = '←'
    return df_relaxed

def relax_direct_to_indirect(df: pd.DataFrame, source: str, target: str) -> pd.DataFrame:
    """
    Turns a direct relation ('→') into an indirect one ('≺' and '≻').
    Turns a parallel relation ('||') into two-ways indirect relation ('≺≻').
    """
    df_relaxed = df.copy()
    if df_relaxed.loc[source, target] == '→':
        df_relaxed.loc[source, target] = '≺'
        df_relaxed.loc[target, source] = '≻'
    elif df_relaxed.loc[source, target]=='||':
        df_relaxed.loc[source, target] = '≺≻'
        df_relaxed.loc[target, source] = '≺≻'
    return df_relaxed


# --- Display Logic ---
def pretty_print_results(title, original_df, updated_df, D, final_E, constraints):
    """Helper function to display all results."""
    print("="*80)
    print(f"Executing for: {title}")
    print("="*80)
    print("\n1. Original Input Matrix:")
    print(original_df)
    print("\n2. Matrix Updated with Transitive Closure Symbols:")
    print(updated_df)
    print("\n3. Parsed Directly-Follows Set (D):")
    print(sorted(list(D)))
    print("\n4. Final Combined Eventually-Follows Set (E):")
    print(sorted(list(final_E)))
    print("\n5. Generated Binary Constraints:")
    if not constraints: print("None")
    else:
        for constraint in sorted(list(constraints), key=lambda x: str(x)):
            print(constraint)
    print("\n\n")

def build_mirrored_matrix(activities, start_activities, primary_relations):
    """Builds a relationally complete matrix with an artificial 'Start' node."""
    full_activities = ['Start'] + activities
    df = pd.DataFrame('-', index=full_activities, columns=full_activities)
    
    for act in start_activities:
        primary_relations.append(('Start', act, '→'))
        
    inverse_map = {'→': '←', '←': '→', '≺': '≻', '≻': '≺', '||': '||'}
    for row_act, col_act, symbol in primary_relations:
        if row_act in full_activities and col_act in full_activities:
            df.loc[row_act, col_act] = symbol
            df.loc[col_act, row_act] = inverse_map.get(symbol, '-')
            
    return df

def perform_relaxation_operations(df):
    """Applies a series of relaxation operations to the matrix."""
    df_relaxed = df.copy()
    # Open and read the JSON file
    with open("relaxation-operations.json", "r", encoding="utf-8") as f:
        data = json.load(f)
    print("Relaxation operations to be applied, if you want to skip any operation, just comment it out in the json (relaxation-operations.json) file.")
    for op in data:
        print(f"Type: {op['type']}, A: {op['A']}, B: {op['B']}")
    print("Applying Relaxation Operation:")
    for op in data:
        #print(f"Type: {op['type']}")
        #print(f"A: {op['A']}")
        #print(f"B: {op['B']}")
        if op['type'] == 1:
            df_relaxed = relax_remove_activity(df_relaxed, op['A'])
        elif op['type'] == 2:
            df_relaxed = relax_remove_all_relationships(df_relaxed, op['A'], op['B'])
        elif op['type'] == 3:
            df_relaxed = relax_exclusive_to_direct(df_relaxed, op['A'], op['B'])
        elif op['type'] == 4:
            df_relaxed = relax_direct_to_indirect(df_relaxed, op['A'], op['B'])
    print("Relaxation operations applied.")
    return df_relaxed

if __name__ == "__main__":

    # Ensure a file path is provided
    if len(sys.argv) != 2:
        print("Usage: python driver.py <txt_file_path>")
        sys.exit(1)

    txt_path = sys.argv[1]

    # Check if file exists
    if not os.path.exists(txt_path):
        print(f"File not found: {txt_path}")
        sys.exit(1)

    # Read and parse the list from file
    with open(txt_path, 'r', encoding='utf-8') as file:
        try:
            content = file.read()
            matrix = ast.literal_eval(content)
        except Exception as e:
            print("Failed to parse the list from the file.")
            print("Error:", e)
            sys.exit(1)

    df1 = pd.DataFrame(matrix[1:], columns=matrix[0])
    # Set first column as index
    df1 = df1.set_index('')
    # Remove the name of the index
    df1.index.name = None
    # Now we have a clean DataFrame
    d1, e1_matrix = parse_relation_matrix(df1)
    e1_tc = compute_transitive_closure(d1)
    updated_df1 = update_matrix_with_tc(df1, e1_tc)
    final_e1 = e1_matrix.union(e1_tc)
    # Store the original DataFrame for reference
    original_df = df1.copy()
    title="BPIC19 Example from Paper"
    while True:
        print("="*80)
        print(f"Executing for: {title}")
        print("="*80)
        print("1. Show original input matrix")
        print("2. Update matrix with transitive closure")
        print("3. Parsed Directly-Follows Set (D):")        
        print("4. Final Combined Eventually-Follows Set (E):")
        print("5. Perform Relaxation Operations on the matrix:")
        print("6. Generated Binary Constraints:")
        print("7. Determine Conformance Rate:")
        print("0. Exit")
        choice = input("Enter your choice (0-7): ")

        if choice == "1": #Show original input matrix
            print("\n1. Original Input Matrix:")
            print(original_df)
        elif choice == "2": #Update matrix with transitive closure
            print("\n2. Matrix Updated with Transitive Closure Symbols:")
            d1, e1_matrix = parse_relation_matrix(df1)
            e1_tc = compute_transitive_closure(d1)
            updated_df1 = update_matrix_with_tc(df1, e1_tc)
            print(updated_df1)
        elif choice == "3": #Parsed Directly-Follows Set (D):
            print("\n3. Parsed Directly-Follows Set (D):")
            d1, e1_matrix = parse_relation_matrix(df1)
            print(sorted(list(d1)))
        elif choice == "4": #Final Combined Eventually-Follows Set (E):
            print("\n4. Final Combined Eventually-Follows Set (E):")
            d1, e1_matrix = parse_relation_matrix(df1)
            e1_tc = compute_transitive_closure(d1)
            updated_df1 = update_matrix_with_tc(df1, e1_tc)
            final_e1 = e1_matrix.union(e1_tc)
            print(sorted(list(final_e1)))
        elif choice == "5": #Perform Relaxation operations on the matrix.
            updated_df1=perform_relaxation_operations(updated_df1)
            d1, final_e1 = parse_relation_matrix(updated_df1)
            #e2_tc = compute_transitive_closure(d2)
            e1_tc=set()
            print("\nRelaxed Matrix:")
            print(updated_df1)
        elif choice == "6": #Generated Binary Constraints:
            constraints = generate_binary_constraints(d1, final_e1,e1_tc)
            print("\n5. Generated Binary Constraints:")
            if not constraints: print("None")
            else:
                for constraint in sorted(list(constraints), key=lambda x: str(x)):
                    print(constraint)
        elif choice == "7": #Conformance Rate
            constraints = generate_binary_constraints(d1, final_e1,e1_tc)
            constraint_strs = [str(constraint) for constraint in constraints]
            determine_conformance_rate_function(constraints)
        elif choice == "0":
            print("Exiting.")
            break
        else:
            print("Invalid choice. Please try again.") 




