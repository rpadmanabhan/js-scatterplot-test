# standard lib
import logging

# 3rd party
import muon
import numpy as np
import plotly.offline as po
import plotly.graph_objs as go
import plotly.express as px
import pyarrow as pa

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


class SingleCellAnalysis:
    def __init__(self):
        self.h5mu_obj = None
        self.unique_cell_types = None

    def load_h5mu(self, h5mu_file):
        LOGGER.info('Entered func')
        self.h5mu_obj = muon.read_h5mu(h5mu_file)
        LOGGER.info('Ended func')

    def return_num_cells(self):
        return self.h5mu_obj.shape[0]
    
    def return_normalized_umap_coords_pyarrow(self):
        ''' Return umap coords stored in the ann data obj
        '''
        LOGGER.info('Entered func')

        umap_coords = self.h5mu_obj['rna'].obsm['X_umap']
        cell_types = self.h5mu_obj['rna'].obs['Cell_Type_Experimental']

        # Get points into Normalized Device coordinates (NDS) i.e. in a [-1, 1] range - this is needed by the library
        #-----------------------------------------------------------------------------
        # Find min and max values for both x and y
        min_vals = np.min(umap_coords, axis=0)
        max_vals = np.max(umap_coords, axis=0)

        # Calculate scaling factors for both x and y
        scale_factors = 2 / (max_vals - min_vals)

        # Perform min-max scaling
        normalized_umap_coords = ((umap_coords - min_vals) * scale_factors) - 1

        # The scatterplot library wants integer labels for coloring so convert string cell types to 0, 1, 2, ... 8 integers
        #-----------------------------------------------------------------------------
        # Get unique cell types
        unique_cell_types = sorted(set(cell_types))

        # Create a dictionary mapping cell types to integers
        cell_type_to_int = {cell_type: idx for idx, cell_type in enumerate(unique_cell_types)}

        # Map strings to integers
        cell_types_mapped_to_int = [cell_type_to_int[cell_type] for cell_type in cell_types]

        data = [
            pa.array(normalized_umap_coords[:,0]),
            pa.array(normalized_umap_coords[:,1]),
            pa.array(cell_types_mapped_to_int, type = pa.int32()),
            pa.array(self.h5mu_obj["rna"].obs_names)
        ]

        # Serialize the Arrow data
        arrow_data = pa.record_batch(
            data,
            names = ['umap_coords_X', 'umap_coords_Y', 'cell_types', 'cell_indices']
        )
        sink = pa.BufferOutputStream()

        with pa.ipc.new_stream(sink, arrow_data.schema) as writer:
            writer.write(arrow_data)

        LOGGER.info('Ended func')
        self.unique_cell_types = unique_cell_types
        return sink.getvalue().to_pybytes()
        #return sink.getvalue().to_pybytes(), unique_cell_types


    def return_simulated_normalized_umap_coords_pyarrow(self):
        '''Simulate a cluster of points from a multivariate normal distribution.
        '''
        LOGGER.info('Starting func')
        N = 5_000_000
        K = 8
        D = 2
        # N => # of points
        # K => # of clusters
        # D => Dimensionality
        
        # Random cluster centers within the range [-1, 1]
        centers = np.random.uniform(-100, 100, size=(K, D))
        
        # Random cluster covariances to create tight clusters
        covariances = np.array([[[np.random.uniform(2, 5), 0], [0, np.random.uniform(2, 5)]] for _ in range(K)])
        
        # Divide the total number of points equally among the clusters
        points_per_cluster = N // K
        
        # Generate points for each cluster
        points = []
        cluster_ids = []
        for k in range(K):
            cluster_points = np.random.multivariate_normal(centers[k], covariances[k], points_per_cluster)
            points.extend(cluster_points)
            cluster_ids.extend([k] * points_per_cluster)

        points = np.array(points)
        # Scale points to the [-1, 1] interval
        min_vals = np.min(points, axis=0)
        max_vals = np.max(points, axis=0)
        scale_factors = 2 / (max_vals - min_vals)
        normalized_points = ((points - min_vals) * scale_factors) - 1
        LOGGER.info(f'Done simulating {N} points, serializing to Apache Arrow IPC format')

        data = [
            pa.array(normalized_points[:,0]),
            pa.array(normalized_points[:,1]),
            pa.array(cluster_ids, type = pa.int32()),
            pa.array(np.arange(0, N))
        ]
        # Serialize the Arrow data
        arrow_data = pa.record_batch(
            data,
            names = ['umap_coords_X', 'umap_coords_Y', 'cell_types', 'obs_names']
        )
        sink = pa.BufferOutputStream()

        with pa.ipc.new_stream(sink, arrow_data.schema) as writer:
            writer.write(arrow_data)

        LOGGER.info('Ended func')
        unique_cell_types = ["B", "Dendritic", "Monocyte_classical", "T_CD4_memory", "T_CD4_naive", "T_CD8_memory", "T_CD8_naive", "T_gamma_delta"]    
        self.unique_cell_types = unique_cell_types
        return sink.getvalue().to_pybytes()

        #return sink.getvalue().to_pybytes(), unique_cell_types


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
