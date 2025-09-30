import pm4py
import re
from pm4py.objects.bpmn.importer import importer as bpmn_importer
from pm4py.objects.log.importer.xes import importer as xes_importer
from pm4py.algo.conformance.alignments.petri_net import algorithm as align_algorithm
from pm4py.objects.conversion.bpmn import converter as bpmn_converter
from pm4py.algo.filtering.log.attributes import attributes_filter
import json
#-------------------------------------------------------
def chain_response(trace,A,B):
    isTraceAffected=False
    violations_in_trace=0
    for i in range(len(trace)):
            if trace[i] == A:
                # Check if next event exists and is in B
                if i + 1 >= len(trace) or trace[i + 1] not in B:
                    violations_in_trace += 1        
            if violations_in_trace > 0:
                isTraceAffected=True
    return isTraceAffected
#---------------------------------------------------------------
def alternate_response(trace,A,B):
    violations_in_trace = 0
    isTraceAffected=False
    i = 0
    while i < len(trace):
        if trace[i] == A:
        
            found_B = False
            j = i + 1
            while j < len(trace):
                if trace[j] in B:
                    found_B = True
                    break
                elif trace[j] == A:
                    break  # next A found before B → violation
                j += 1
            if not found_B:
                violations_in_trace += 1
            i = j  # continue from where we left off
        else:
            i += 1

    # if there are violations, then the trace is being affected        
    if violations_in_trace > 0:
            isTraceAffected=True
    
    return isTraceAffected
#--------------------------------------------------------------------
def not_cooccurance(trace,A,B):
    
    violations_in_trace=0
    isTraceAffected=False
    if A == B:
            # Violation if the same activity occurs more than once
            violations_in_trace = 1 if trace.count(A) > 1 else 0
    else:
        # Violation if both A and B occur together
        violations_in_trace = 1 if (A in trace and B in trace) else 0

    if violations_in_trace > 0:
            isTraceAffected=True
    return isTraceAffected
#-------------------------------------------------------------
def init_violation(trace, A):

    violations_in_trace=0
    isTraceAffected=False
    if not trace or trace[0] not in A:
        violations_in_trace += 1
        isTraceAffected=True
        
    return isTraceAffected
#-----------------------------------------------------------
def end_violation(trace, A):
 
    violations_in_trace=0
    isTraceAffected=False
    
    if not trace or trace[-1] not in A:
        violations_in_trace += 1
        isTraceAffected=True
        

    return isTraceAffected
#-----------------------------------------------------------
def parse_constraint_strings(constraint_strs):
    ############ Load the abbreviation to full name mapping ############
    with open('sabbrev_to_full.json', 'r') as f:
        sabbrev_to_full = json.load(f)
    ##################################################################

    if sabbrev_to_full is None:
            raise ValueError("The abbreviation to full name mapping could not be loaded.")
           
    constraints = []
    for constraint in constraint_strs:
        # If constraint is a string, parse as before
        if isinstance(constraint, str):
            type_match = re.match(r"(ChainResponse|AlternateResponse|AlternateResponse_P)\(", constraint)
            if not type_match:
                continue
            constraint_type = type_match.group(1)
            antecedent = re.search(r"antecedent=frozenset\(\{([^\}]*)\}\)", constraint)
            consequent = re.search(r"consequent=frozenset\(\{([^\}]*)\}\)", constraint)
            if not antecedent or not consequent:
                continue
            antecedent_abbr = [x.strip().strip("'") for x in antecedent.group(1).split(",") if x.strip()]
            consequent_abbr = [x.strip().strip("'") for x in consequent.group(1).split(",") if x.strip()]
        # If constraint is a namedtuple, extract fields directly
        elif hasattr(constraint, "_fields"):
            constraint_type = type(constraint).__name__
            antecedent_abbr = list(constraint.antecedent)
            consequent_abbr = list(constraint.consequent)
        else:
            continue  # skip unknown types

        
        # Map to full forms
        antecedent_full = sabbrev_to_full.get(antecedent_abbr[0], antecedent_abbr[0])
        consequent_full = [sabbrev_to_full.get(abbr, abbr) for abbr in consequent_abbr]

        constraint_dict = {
            "type": constraint_type,
            "A": antecedent_full,
            "B": consequent_full
        }
        constraints.append(constraint_dict)
    return constraints
#--------------------- Determine Conformance Rate -----------------------
def determine_conformance_rate_function(constraint_strs):
    
    print("Determining Conformance Rate...")
    print("Loading event log...")
    # 1. Load the event log
    log_path = "BPIC19_3way_IbeforeGR_standardPO_complete.xes"
    log = xes_importer.apply(log_path)
    print("Parsing constraints...")
    constraints = parse_constraint_strings(constraint_strs)
    #print(constraints)
    constraints.append({"type": "Init", "A": ["Create Purchase Requisition Item","Create Purchase Order Item"], "B": ""})
    print(f"Total number of constraints: {len(constraints)}")
    listOfConformTraces=[]
    listOfAfftectedTraces=[]

    print("Evaluating traces against constraints...")
    for trace_idx, trace in enumerate(log):
        trace = [event["concept:name"] for event in log[trace_idx]]
        isTraceAffected=False
        for constraint in constraints:
            constraint_type = constraint["type"]
            A = constraint["A"]
            B = constraint["B"]
            
            if constraint_type=="Init":
                isTraceAffected=init_violation(trace,A)
                if isTraceAffected==True:
                    listOfAfftectedTraces.append(trace)
                    break
            elif constraint_type=="AlternateResponse":
                isTraceAffected=alternate_response(trace,A,B)
                if isTraceAffected==True:
                    find_constraints = [c for c in constraints if c["A"] == A and c["type"] == "ChainResponse"]
                    if not find_constraints:
                        listOfAfftectedTraces.append(trace)
                        break
                    else:
                        for find_constraint in find_constraints:
                            find_A=find_constraint["A"]
                            find_B=find_constraint["B"]
                            isTraceAffected=False
                            isTraceAffected=chain_response(trace,find_A,find_B)
                            if isTraceAffected==True:
                                listOfAfftectedTraces.append(trace)
                                break
            elif constraint_type=="ChainResponse":
                isTraceAffected=chain_response(trace,A,B)
                if isTraceAffected==True:
                    find_constraints = [c for c in constraints if c["A"] == A and c["type"] == "AlternateResponse"]
                    if not find_constraints:
                        listOfAfftectedTraces.append(trace)
                        break
                    else:
                        for find_constraint in find_constraints:
                            find_A=find_constraint["A"]
                            find_B=find_constraint["B"]
                            isTraceAffected=False
                            isTraceAffected=alternate_response(trace,find_A,find_B)
                            if isTraceAffected==True:
                                listOfAfftectedTraces.append(trace)
                                break
                    
            elif constraint_type=="AlternateResponse_P":
                isTraceAffected=alternate_response(trace,A,B)
                if isTraceAffected==True:
                    listOfAfftectedTraces.append(trace)
                    break
            
        if isTraceAffected==False:
            listOfConformTraces.append(trace)
    
    print(f"Length of listOfConformTraces: ",len(listOfConformTraces))
    print(f"Length of listOfAfftectedTraces: ",len(listOfAfftectedTraces))
    print(f"Total number of traces in the log: ",len(log))
    print(f"Conformance Rate:", len(listOfConformTraces)/len(log))    
   
   
    