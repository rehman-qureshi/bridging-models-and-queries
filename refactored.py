from collections import namedtuple
import pandas as pd


# Define the structure for the declarative constraints for clarity
Init = namedtuple('Init', ['activities'])
ChainResponse = namedtuple('ChainResponse', ['antecedent', 'consequent'])
AlternateResponse = namedtuple('AlternateResponse', ['antecedent', 'consequent'])


def get_start_activities(D, all_activities):
    """
    Identifies start activities from the set of directly-follows relations.
    Start activities are those that never appear as a consequent.
    """
    consequents = {b for a, b in D}
    start_activities = all_activities - consequents
    return start_activities


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

        if is_forward and is_backward:
            # Handle bidirectional case: '≺≻'
            if updated_df.loc[a, b] not in strong_symbols:
                updated_df.loc[a, b] = '≺≻'
            if updated_df.loc[b, a] not in strong_symbols:
                updated_df.loc[b, a] = '≺≻'
            processed_pairs.add((a, b))
            processed_pairs.add((b, a))
        elif is_forward:
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


def generate_constraints(D, E, all_activities):
    """
    Generates a set of declarative binary constraints based on directly-follows (D)
    and eventually-follows (E) relations, using the detailed IsOptionalActivity logic.

    Args:
        D (set): A set of tuples (a, b) representing that activity b directly follows a.
        E (set): A set of tuples (a, b) representing that activity b eventually follows a.
        all_activities (list): A list of all activities in the process.

    Returns:
        set: A set of declarative constraints (Init, ChainResponse and AlternateResponse).
    """
    C = set()

    # Add Init constraint for identified start activities
    start_activities = get_start_activities(D, set(all_activities))
    if start_activities:
        C.add(Init(activities=frozenset(start_activities)))
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
                    if not is_optional_activity(b, D):
                        C.add(AlternateResponse(antecedent=frozenset({a}), consequent=frozenset({b})))
                    if not is_optional_activity(c, D):
                        C.add(AlternateResponse(antecedent=frozenset({a}), consequent=frozenset({c})))

    A_E = {a for a, b in E}
    for a in A_E:
        S = {x for source, x in E if source == a and (source, x) not in D and (source, x) not in compute_transitive_closure(D)}
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
    if df_relaxed.loc[source, target] == '-':
        df_relaxed.loc[source, target] = '→'
        df_relaxed.loc[target, source] = '←'
    return df_relaxed

def relax_direct_to_indirect(df: pd.DataFrame, source: str, target: str) -> pd.DataFrame:
    """
    Turns a direct relation ('→') into an indirect one ('≺' and '≻').
    """
    df_relaxed = df.copy()
    if df_relaxed.loc[source, target] == '→':
        df_relaxed.loc[source, target] = '≺'
        df_relaxed.loc[target, source] = '≻'
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

def build_mirrored_matrix(activities, primary_relations):
    """
    Builds a relationally complete matrix.
    """
    df = pd.DataFrame('-', index=activities, columns=activities)

    inverse_map = {'→': '←', '←': '→', '≺': '≻', '≻': '≺', '||': '||'}
    for row_act, col_act, symbol in primary_relations:
        if row_act in activities and col_act in activities:
            df.loc[row_act, col_act] = symbol
            df.loc[col_act, row_act] = inverse_map.get(symbol, '-')

    return df


if __name__ == "__main__":
    activities1 = ['CPR', 'KPR', 'CPO', 'RG', 'PQC', 'RI', 'SP', 'CO', 'RR']
    data1 = [
        ['-', '→', '-', '-', '-', '-', '-', '-', '-'],
        ['←', '-', '→', '-', '-', '-', '-', '-', '→'],
        ['-', '←', '-', '→', '-', '-', '-', '-', '-'],
        ['-', '-', '←', '-', '→', '-', '-', '-', '-'],
        ['-', '-', '-', '←', '-', '→', '-', '-', '-'],
        ['-', '-', '-', '-', '←', '-', '→', '-', '-'],
        ['-', '-', '-', '-', '-', '←', '-', '→', '-'],
        ['-', '-', '-', '-', '-', '-', '←', '-', '-'],
        ['-', '←', '-', '-', '-', '-', '-', '-', '-']
    ]
    df1 = pd.DataFrame(data1, index=activities1, columns=activities1)
    d1, e1_matrix = parse_relation_matrix(df1)
    e1_tc = compute_transitive_closure(d1)
    updated_df1 = update_matrix_with_tc(df1, e1_tc)
    final_e1 = e1_matrix.union(e1_tc)
    all_activities1 = set(df1.columns)
    constraints = generate_constraints(d1, final_e1, all_activities1)
    pretty_print_results("Running Example from Paper", df1, updated_df1, d1, final_e1, constraints)

    activities = ['A', 'B', 'C', 'D']
    primary_relations = [('A', 'B', '→'), ('B', 'C', '||'), ('C', 'D', '→')]
    df = build_mirrored_matrix(activities, primary_relations)
    d, e_matrix = parse_relation_matrix(df)
    e_tc = compute_transitive_closure(d)
    updated_df = update_matrix_with_tc(df, e_tc)
    final_e = e_matrix.union(e_tc)
    all_activities = set(df.columns)
    constraints = generate_constraints(d, final_e, all_activities)
    pretty_print_results("Simple Example with Parallelism", df, updated_df, d, final_e, constraints)

    activities = ['A', 'B', 'C', 'D']
    primary_relations = [('A', 'B', '→'), ('A', 'C', '→'), ('A', 'D', '→'), ('B', 'C', '||'), ('B', 'D', '→'), ('C', 'D', '→')]
    df = build_mirrored_matrix(activities, primary_relations)
    e_tc = compute_transitive_closure(d)
    updated_df = update_matrix_with_tc(df, e_tc)
    final_e = e_matrix.union(e_tc)
    all_activities = set(df.columns)
    constraints = generate_constraints(d, final_e, all_activities)
    pretty_print_results("Example with Parallelism", df, updated_df, d, final_e, constraints)




