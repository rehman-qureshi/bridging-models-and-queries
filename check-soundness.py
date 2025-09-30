# check_soundness.py
# Requires: pip install pm4py

import sys

def load_pnml(path):
    import pm4py
    # Try convenient wrapper first (pm4py.read_pnml), otherwise use importer variants
    try:
        net, im, fm = pm4py.read_pnml(path)
        return net, im, fm
    except Exception:
        # fallback to more explicit importer
        from pm4py.objects.petri import importer as pn_importer
        from pm4py.objects.petri.importer.variants import pnml as pnml_variant
        # Some PM4Py versions expose different helpers; try common ones
        try:
            net, im, fm = pnml_variant.import_net(path)
            return net, im, fm
        except Exception:
            # another common name
            net, im, fm = pnml_variant.import_net_from_string(open(path,'rb').read())
            return net, im, fm

def check_soundness_with_pm4py(net, im, fm):
    # Try importing the soundness utilities from a couple of locations (PM4Py API evolved)
    try:
        from pm4py.objects.petri.check_soundness import (
            check_wfnet,
            check_easy_soundness_of_wfnet
        )
        is_wfnet = check_wfnet(net)
        easy_sound = check_easy_soundness_of_wfnet(net)
        return {"is_wfnet": is_wfnet, "easy_sound": easy_sound}
    except Exception:
        # fallback location
        try:
            from pm4py.objects.petri_net.utils.check_soundness import (
                check_wfnet, check_easy_soundness_of_wfnet
            )
            is_wfnet = check_wfnet(net)
            easy_sound = check_easy_soundness_of_wfnet(net)
            return {"is_wfnet": is_wfnet, "easy_sound": easy_sound}
        except Exception as e:
            raise RuntimeError("Could not find PM4Py soundness API in this installation: " + str(e))

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python check_soundness.py path/to/model.pnml")
        sys.exit(1)

    path = sys.argv[1]
    net, im, fm = load_pnml(path)
    print("Loaded PNML.")
    res = check_soundness_with_pm4py(net, im, fm)
    print("Is WF-net?        :", res["is_wfnet"])
    print("Easy soundness?   :", res["easy_sound"])

    # Interpretation hints:
    # - is_wfnet False => structure not a workflow net (unique source/sink conditions fail)
    # - easy_sound True => net passes PM4Py's 'easy soundness' check (basic checks implemented there)
    #
    # If you need explicit counterexamples (e.g., which transitions are dead or
    # why final marking not reachable) you may need a reachability analysis
    # (state-space exploration) or use external tools like WOFLAN/ProM.
