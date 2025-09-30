from pm4py.objects.petri_net.importer import importer as pnml_importer
from pm4py.visualization.petri_net import visualizer as pn_visualizer
import os


def visualize_function(pnml_file):
    """
    Visualizes a PNML file using PM4Py.

    Parameters:
        pnml_file (str): Path to the PNML file.
    """
     # Load the Petri net from PNML
    net, initial_marking, final_marking = pnml_importer.apply(pnml_file)
        

    # Visualize the net
    gviz = pn_visualizer.apply(net, initial_marking, final_marking)

    # Determine the output directory (process_model folder in the parent directory)
    parent_dir = os.path.dirname(os.path.dirname(pnml_file))
    output_dir = os.path.join(parent_dir, "output")
    os.makedirs(output_dir, exist_ok=True)  # Create the folder if it doesn't exist

    # Save the visualization as a PNG file
    output_file = os.path.join(output_dir, os.path.splitext(os.path.basename(pnml_file))[0] + ".png")
    pn_visualizer.save(gviz, output_file)
    print(f"Visualization saved as {output_file}")
    return output_file
