# standard lib
import logging
from xmlrpc.server import SimpleXMLRPCServer
from xmlrpc.server import SimpleXMLRPCRequestHandler

# 3rd party
import muon
import numpy as np
import scanpy as sc
import plotly.offline as po
import plotly.graph_objs as go
import plotly.express as px

# Some basic LOGGER
# -------------------------------------------------------------------------------------------------
LOGGER = logging.getLogger(__file__)
handler = logging.StreamHandler()
formatter = logging.Formatter(
    "%(asctime)s.%(msecs)03d - %(levelname)s - %(funcName)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
handler.setFormatter(formatter)
LOGGER.addHandler(handler)
LOGGER.setLevel(logging.INFO)


class RequestHandler(SimpleXMLRPCRequestHandler):
    # Restrict to a particular path.
    rpc_paths = ('/RPC2',)

    def do_OPTIONS(self):
        self.send_response(200)
        self.end_headers()

    # cors headers
    def end_headers(self) -> None:
        self.send_header(
                "Access-Control-Allow-Headers",
                "Origin, X-Requested-With, Content-Type, Accept")
        self.send_header("Access-Control-Allow-Origin", "*")
        SimpleXMLRPCRequestHandler.end_headers(self)

class BackendService:
    def __init__(self):
        self.h5mu_obj = None

    def add(self, x, y):
        return x + y
    
    def load_h5mu(self, h5mu_file):
        LOGGER.info('Entered func')
        self.h5mu_obj = muon.read_h5mu(h5mu_file)
        LOGGER.info('Ended func')

    def return_num_cells(self):
        return self.h5mu_obj.shape[0]
    
    def return_umap_coords(self):
        LOGGER.info('Entered func')
        umap_x = self.h5mu_obj["rna"].obsm['X_umap'][:, 0]
        umap_y = self.h5mu_obj["rna"].obsm['X_umap'][:, 1]
        cell_types = self.h5mu_obj["rna"].obs['Cell_Type_Experimental']
        LOGGER.info('Ended func')
        return umap_x.tolist(), umap_y.tolist(), cell_types.tolist()

    def return_normalized_umap_coords_naive(self):
        LOGGER.info('Entered func')
        umap_x = self.h5mu_obj["rna"].obsm['X_umap'][:, 0]
        umap_y = self.h5mu_obj["rna"].obsm['X_umap'][:, 1]
        cell_types = self.h5mu_obj["rna"].obs['Cell_Type_Experimental']
        # Calculate the minimum and maximum values for umap_x and umap_y
        min_x, max_x = np.min(umap_x), np.max(umap_x)
        min_y, max_y = np.min(umap_y), np.max(umap_y)
        # Normalize umap_x and umap_y to the range [-1, 1]
        normalized_umap_x = 2 * ((umap_x - min_x) / (max_x - min_x)) - 1
        normalized_umap_y = 2 * ((umap_y - min_y) / (max_y - min_y)) - 1
        # Return the normalized UMAP coordinates along with cell types
        LOGGER.info('Ended func')
        return normalized_umap_x.tolist(), normalized_umap_y.tolist(), cell_types.tolist()
    
    def return_normalized_umap_coords(self):
        LOGGER.info('Entered func')

        umap_coords = self.h5mu_obj["rna"].obsm['X_umap']
        cell_types = self.h5mu_obj["rna"].obs['Cell_Type_Experimental']

        # Find min and max values for both x and y
        min_vals = np.min(umap_coords, axis=0)
        max_vals = np.max(umap_coords, axis=0)

        # Calculate scaling factors for both x and y
        scale_factors = 2 / (max_vals - min_vals)

        # Perform min-max scaling
        normalized_umap_coords = ((umap_coords - min_vals) * scale_factors) - 1

        # Get unique cell types
        unique_cell_types = sorted(set(cell_types))

        # Create a dictionary mapping cell types to integers
        cell_type_to_int = {cell_type: idx for idx, cell_type in enumerate(unique_cell_types)}

        # Map strings to integers
        cell_types_mapped_to_int = [cell_type_to_int[cell_type] for cell_type in cell_types]

        # Return the normalized UMAP coordinates along with cell types
        return (
            normalized_umap_coords[:,0].tolist(),
            normalized_umap_coords[:,1].tolist(),
            cell_types_mapped_to_int,
            unique_cell_types,
            self.h5mu_obj["rna"].obs_names.tolist()
        )


    def return_umap_scatter_html(self):
        LOGGER.info('Entered func')

        umap_x = self.h5mu_obj["rna"].obsm['X_umap'][:, 0]
        umap_y = self.h5mu_obj["rna"].obsm['X_umap'][:, 1]
        cell_types = self.h5mu_obj["rna"].obs['Cell_Type_Experimental']

        # Get unique cell types and assign a color to each
        unique_cell_types = cell_types.unique()
        num_unique_cell_types = len(unique_cell_types)
        color_palette = px.colors.qualitative.Set3[:num_unique_cell_types]

        # Create a dictionary mapping unique cell types to colors
        cell_type_colors = dict(zip(unique_cell_types, color_palette))

        # Iterate over each unique cell type and plot them separately
        scatter_traces = []
        for cell_type in unique_cell_types:
            # filter data points for the current cell type
            mask = (cell_types == cell_type)
            cell_umap_x = umap_x[mask]
            cell_umap_y = umap_y[mask]

            # Create a scatter trace for the current cell type with its assigned color
            scatter_trace = go.Scattergl(
                x = cell_umap_x,
                y = cell_umap_y,
                mode = 'markers',
                marker = dict(
                    size = 5,
                    color = cell_type_colors[cell_type]
                ),
                name = cell_type
            )

            scatter_traces.append(scatter_trace)

        # Create the figure with all scatter traces
        fig = go.Figure(data = scatter_traces)
        fig.update_layout(
            title = "UMAP Coordinates",
            xaxis_title = "UMAP X",
            yaxis_title = "UMAP Y"
        )
        
        plotly_html = po.plot(fig, include_plotlyjs=False, output_type='div')
        LOGGER.info('Ended func')
        return plotly_html

if __name__ == '__main__':
    # Create server
    with SimpleXMLRPCServer(('localhost', 8000),
                            requestHandler=RequestHandler, allow_none=True) as server:
        server.register_introspection_functions()

        server.register_instance(BackendService())

        # Run the server's main loop
        print("Server is running on port 8000...")
        server.serve_forever()