# stdlib
from io import BytesIO
import tempfile

# 3rd party
from flask import Flask, jsonify, request, send_file
from flask_cors import CORS

# ours
from analysis import SingleCellAnalysis

analysis_obj = SingleCellAnalysis()

app = Flask(__name__)
CORS(app)

# Route for loading H5MU files
@app.route("/load_h5mu", methods=["POST"])
def load_h5mu():
    try:
        # Retrieve the uploaded file from the request's form data
        file = request.files["file"]
        
        # Create a temporary file
        with tempfile.NamedTemporaryFile(delete=True) as temp_file:
            temp_file_path = temp_file.name
            
            # Save the file to the temporary file
            file.save(temp_file_path)
        
            # Call the backend service function to load the H5MU file with the file path
            analysis_obj.load_h5mu(temp_file_path)
        
        # Return a JSON response indicating success
        return jsonify({"message": "H5MU file loaded successfully"}), 200
    except Exception as e:
        print(str(e))
        # Return a JSON response with error message in case of any exception
        return jsonify({"error": str(e)}), 400

# Route for returning number of cells
@app.route("/return_num_cells")
def return_num_cells():
    return jsonify({"num_cells": analysis_obj.return_num_cells()})

@app.route("/unique_cell_types")
def get_unique_cell_types():
    unique_cell_types = analysis_obj.unique_cell_types
    return jsonify(unique_cell_types)

# Route for returning normalized UMAP coordinates as Arrow data
@app.route("/return_normalized_umap_coords_pyarrow")
def return_normalized_umap_coords_pyarrow():
    arrow_pybytes = analysis_obj.return_normalized_umap_coords_pyarrow()
    return send_file(BytesIO(arrow_pybytes), 'data.arrow')

# Route for returning simulated UMAP coordinates as Arrow data - for testing scaling to larger number of points
@app.route("/return_simulated_normalized_umap_coords_pyarrow")
def return_simulated_normalized_umap_coords_pyarrow():
    arrow_pybytes = analysis_obj.return_simulated_normalized_umap_coords_pyarrow()
    return send_file(BytesIO(arrow_pybytes), 'data.arrow')

# Route for returning the plotly html div
@app.route("/return_plotly_html_div")
def return_plotly_html_div():
    return jsonify(analysis_obj.return_umap_scatter_html())