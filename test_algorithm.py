# TODO transitive closure for loops of length 2


from refactored import (
    Init,
    build_mirrored_matrix,
    parse_relation_matrix,
    compute_transitive_closure,
    generate_constraints,
    ChainResponse,
    AlternateResponse,
)


def run_pipeline_no_tc(df):
    """Takes a DataFrame and returns the final set of constraints."""
    d, e = parse_relation_matrix(df)
    all_activities = set(df.columns)
    constraints = generate_constraints(d, e, all_activities)
    return constraints


def run_full_pipeline(df):
    """Takes a DataFrame, computes transitive closure, and returns the final set of constraints."""
    d, e_matrix = parse_relation_matrix(df)
    e_tc = compute_transitive_closure(d)
    final_e = e_matrix.union(e_tc)
    all_activities = set(df.columns)
    constraints = generate_constraints(d, final_e, all_activities)
    return constraints


def test_pattern_exclusive_choice():
    """Tests an exclusive choice: Start -> A -> {B XOR C} -> D."""
    activities = ['A', 'B', 'C', 'D']
    primary_relations = [('A', 'B', '→'), ('A', 'C', '→'), ('B', 'D', '→'), ('C', 'D', '→')]
    df = build_mirrored_matrix(activities, primary_relations)
    
    expected_constraints = {
        ChainResponse(frozenset({'A'}), frozenset({'B', 'C'})),
        ChainResponse(frozenset({'B'}), frozenset({'D'})),
        ChainResponse(frozenset({'C'}), frozenset({'D'})),

        Init(activities=frozenset({'A'})),
    }
    assert run_full_pipeline(df) == expected_constraints

def test_pattern_parallelism_without_bypass():
    """Tests a parallel flow: Start -> A -> (B || C) -> D."""
    activities = ['A', 'B', 'C', 'D']
    primary_relations = [('A', 'B', '→'), ('A', 'C', '→'), ('B', 'C', '||'), ('B', 'D', '→'), ('C', 'D', '→')]
    df = build_mirrored_matrix(activities, primary_relations)
    
    expected_constraints = {
        ChainResponse(frozenset({'A'}), frozenset({'B', 'C'})),
        ChainResponse(frozenset({'B'}), frozenset({'C', 'D'})),
        ChainResponse(frozenset({'C'}), frozenset({'B', 'D'})),

        Init(activities=frozenset({'A'})),

        AlternateResponse(frozenset({'A'}), frozenset({'B'})),
        AlternateResponse(frozenset({'A'}), frozenset({'C'})),
    }
    assert run_full_pipeline(df) == expected_constraints
    
def test_pattern_parallelism_with_bypass():
    """Tests a parallel flow with bypass: Start -> A -> (B || C) -> D, plus A -> D."""
    activities = ['A', 'B', 'C', 'D']
    primary_relations = [('A', 'B', '→'), ('A', 'C', '→'), ('A', 'D', '→'), ('B', 'C', '||'), ('B', 'D', '→'), ('C', 'D', '→')]
    df = build_mirrored_matrix(activities, primary_relations)
    
    expected_constraints = {
        ChainResponse(frozenset({'A'}), frozenset({'B', 'C', 'D'})),
        ChainResponse(frozenset({'B'}), frozenset({'C', 'D'})),
        ChainResponse(frozenset({'C'}), frozenset({'B', 'D'})),

        Init(activities=frozenset({'A'})),
    }
    assert run_full_pipeline(df) == expected_constraints

def test_pattern_structured_loop():
    """Tests a structured loop: Start -> A -> B -> C -> B ... -> D."""
    activities = ['A', 'B', 'C', 'D']
    primary_relations = [('A', 'B', '→'), ('B', 'C', '||'), ('C', 'D', '→')]
    df = build_mirrored_matrix(activities, primary_relations)
    
    expected_constraints = {
        ChainResponse(frozenset({'A'}), frozenset({'B'})),
        ChainResponse(frozenset({'B'}), frozenset({'C'})),
        ChainResponse(frozenset({'C'}), frozenset({'B', 'D'})),

        Init(activities=frozenset({'A'})),
    }
    assert run_full_pipeline(df) == expected_constraints

def test_pattern_multiple_start_activities():
    """Tests a process that can start with either A or B."""
    activities = ['A', 'B', 'C']
    primary_relations = [('A', 'C', '→'), ('B', 'C', '→')]
    df = build_mirrored_matrix(activities, primary_relations)

    expected_constraints = {
        # Start can be followed by A or B
        ChainResponse(frozenset({'A'}), frozenset({'C'})),
        ChainResponse(frozenset({'B'}), frozenset({'C'})),
        
        Init(activities=frozenset({'B', 'A'}))
    }
    assert run_full_pipeline(df) == expected_constraints